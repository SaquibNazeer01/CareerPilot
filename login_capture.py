"""
Platform Login Session Capture & Connector
Supports both:
1. Automated direct login using credentials from .env
2. Manual login in a real browser window with automatic session detection

Usage:
    python login_capture.py naukri
    python login_capture.py linkedin
"""
import sys
import os
import time
import json
import threading
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from playwright.sync_api import sync_playwright

SITES = {
    "naukri": "https://www.naukri.com/nlogin/login",
    "linkedin": "https://www.linkedin.com/login",
}

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def get_credentials(site: str):
    """Retrieves username and password for the site from env vars or .env file."""
    u = os.environ.get(f"{site.upper()}_USERNAME") or os.environ.get(f"{site.upper()}_EMAIL")
    p = os.environ.get(f"{site.upper()}_PASSWORD")

    if not (u and p) and ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k in (f"{site.upper()}_USERNAME", f"{site.upper()}_EMAIL") and not u:
                            u = v
                        elif k == f"{site.upper()}_PASSWORD" and not p:
                            p = v
        except Exception:
            pass

    return (u.strip() if u else None, p.strip() if p else None)


def try_autofill_linkedin(page, username, password):
    """Fills credentials on LinkedIn login page and clicks submit."""
    print("  [Auto-Login] Locating LinkedIn username & password fields...", flush=True)
    try:
        user_input = page.wait_for_selector(
            'input#username, input#session_key, input[name="session_key"], input[type="email"], input[type="text"]',
            timeout=8000
        )
        if user_input:
            user_input.fill(username)
            time.sleep(0.4)
            pass_input = page.wait_for_selector(
                'input#password, input#session_password, input[name="session_password"], input[type="password"]',
                timeout=5000
            )
            if pass_input:
                pass_input.fill(password)
                time.sleep(0.5)
                submit_btn = page.query_selector(
                    'button[type="submit"], button:has-text("Sign in"), button[aria-label*="Sign in"]'
                )
                if submit_btn:
                    print("  [Auto-Login] Submitting credentials...", flush=True)
                    submit_btn.click()
                    return True
    except Exception as e:
        print(f"  (Auto-fill notice: {e})", flush=True)
    return False


def try_autofill_naukri(page, username, password):
    """Fills credentials on Naukri login page and clicks submit."""
    print("  [Auto-Login] Locating Naukri username & password fields...", flush=True)
    try:
        login_btn = page.query_selector('a#login_Layer, a:has-text("Login")')
        if login_btn and not page.query_selector('#usernameField'):
            login_btn.click()
            time.sleep(1)

        user_input = page.wait_for_selector('#usernameField, input[placeholder*="Email"], .login-layer input[type="text"]', timeout=8000)
        if user_input:
            user_input.fill(username)
            time.sleep(0.4)
            pass_input = page.wait_for_selector('#passwordField, input[type="password"]', timeout=5000)
            if pass_input:
                pass_input.fill(password)
                time.sleep(0.5)
                submit_btn = page.query_selector('button[type="submit"], button.loginButton, button:has-text("Login")')
                if submit_btn:
                    print("  [Auto-Login] Submitting credentials...", flush=True)
                    submit_btn.click()
                    return True
    except Exception as e:
        print(f"  (Auto-fill notice: {e})", flush=True)
    return False


def is_authenticated(site: str, context, page) -> bool:
    """Verifies whether the browser session has genuine authenticated cookies/state."""
    try:
        cookies = context.cookies()
        if site == "linkedin":
            has_li_at = any(c.get("name") == "li_at" and len(c.get("value", "")) > 10 for c in cookies)
            if has_li_at:
                return True
            curr_url = page.url.lower()
            return any(k in curr_url for k in ["/feed", "/mynetwork", "/messaging", "/jobs"]) and "/login" not in curr_url and "/checkpoint" not in curr_url
        elif site == "naukri":
            curr_url = page.url.lower()
            if any(k in curr_url for k in ["/mnjuser/homepage", "/mnjuser/profile", "my.naukri.com"]) and "/login" not in curr_url:
                return True
            return any(c.get("name") in ["AUTHTOKEN", "NUKL", "nauk_att", "naukri_user_id"] for c in cookies)
    except Exception:
        pass
    return False


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SITES:
        print(f"Usage: python login_capture.py [{'|'.join(SITES)}]", flush=True)
        sys.exit(1)

    site = sys.argv[1]
    url = SITES[site]
    out_path = f"session_{site}.json"

    username, password = get_credentials(site)

    print(f"🚀 Initializing visible browser for {site.upper()} connection...", flush=True)
    with sync_playwright() as p:
        launch_kwargs = {
            "headless": False,
            "ignore_default_args": ["--enable-automation"],
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        }
        try:
            print("  Opening browser with Chrome channel...", flush=True)
            browser = p.chromium.launch(channel="chrome", **launch_kwargs)
        except Exception:
            print("  Falling back to bundled Chromium browser...", flush=True)
            browser = p.chromium.launch(**launch_kwargs)

        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {},
            };
        """)

        page = context.new_page()
        print(f"🌐 Navigating to {url} ...", flush=True)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  (Notice: Initial page load was slow, but window is open: {e})", flush=True)

        # Attempt auto-fill if credentials are configured
        if username and password:
            print(f"🔑 Saved credentials found for {username[:4]}***. Auto-filling login form...", flush=True)
            if site == "linkedin":
                try_autofill_linkedin(page, username, password)
            elif site == "naukri":
                try_autofill_naukri(page, username, password)
        else:
            print(f"ℹ️ No saved credentials found in .env. Please enter your login in the browser.", flush=True)

        print("\n" + "=" * 60, flush=True)
        print(f"✅ Browser window is open on your desktop!", flush=True)
        print(f"👉 If an OTP, 2FA prompt, or CAPTCHA appears, please complete it in the window.", flush=True)
        print(f"🤖 Auto-Detector: The studio will automatically detect when login succeeds!", flush=True)
        print(f"💾 Manual Option: You can also click 'Save Session Now' once you reach your home feed.", flush=True)
        print("=" * 60 + "\n", flush=True)

        # Background thread for manual stdin trigger
        user_signaled = threading.Event()
        def stdin_worker():
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line and line != "\n" and line != "":
                        break
                    user_signaled.set()
                except Exception:
                    break
        t = threading.Thread(target=stdin_worker, daemon=True)
        t.start()

        # Monitoring loop (polls every 1.5 seconds)
        session_saved = False
        start_time = time.time()
        max_wait_seconds = 300  # 5 minutes

        while time.time() - start_time < max_wait_seconds:
            # Check if login already authenticated
            if is_authenticated(site, context, page):
                print(f"\n🎉 [VERIFIED] Authentication detected! Capturing active session cookies...", flush=True)
                time.sleep(2)  # Allow storage & token refresh to settle
                context.storage_state(path=out_path)
                print(f"💾 Session successfully saved to {out_path}!", flush=True)
                print(f"✨ {site.title()} is now connected and ready for automation!\n", flush=True)
                session_saved = True
                break

            # Check manual trigger from user
            if user_signaled.is_set():
                user_signaled.clear()
                if is_authenticated(site, context, page):
                    print(f"\n🎉 [VERIFIED] Session confirmed! Saving to {out_path}...", flush=True)
                    time.sleep(1)
                    context.storage_state(path=out_path)
                    print(f"💾 Saved {out_path} successfully!\n", flush=True)
                    session_saved = True
                    break
                else:
                    print(f"\n⚠️ Notice: Still on login or checkpoint page (auth token not yet present).", flush=True)
                    print(f"   Please complete login in the opened window. Watching for login...", flush=True)

            time.sleep(1.5)

        if not session_saved:
            # Final check before closing
            if is_authenticated(site, context, page):
                context.storage_state(path=out_path)
                print(f"💾 [SAVED] {out_path} updated.", flush=True)
            else:
                print(f"\n⚠️ Session capture ended without confirmed login.", flush=True)

        browser.close()


if __name__ == "__main__":
    main()
