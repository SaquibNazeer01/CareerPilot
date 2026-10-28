"""
LinkedIn Easy Apply automation bot.
Requires a valid session_linkedin.json generated via login_capture.py.

Usage:
    python linkedin_apply.py
"""
import sys
import os

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import csv
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from common.profile import Profile
from common import llm
from common import learned_answers
from common.human_input import ask_user

SESSION_FILE = "session_linkedin.json"
LOG_FILE = "applications_log.csv"

STOP_PHRASES = [
    "easy apply limit",
    "unusual activity",
    "verify it's you",
    "captcha",
    "security verification",
    "we've restricted",
    "temporarily restricted",
]


class SkipJob(Exception):
    """Raised to skip the current listing and continue the run."""
    pass


class StopRun(Exception):
    """Raised to safely stop the entire automation run."""
    pass


def log_row(row: list):
    new_file = not Path(LOG_FILE).exists()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "source", "title", "company", "status", "reason"])
        w.writerow(row)


def load_already_applied() -> set[tuple[str, str]]:
    """Reads applications_log.csv so previously applied jobs are skipped immediately."""
    if not Path(LOG_FILE).exists():
        return set()
    applied = set()
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 5 and row[4].strip().lower() == "applied":
                    title = (row[2] or "").strip().lower()
                    company = (row[3] or "").strip().lower()
                    if title and company:
                        applied.add((title, company))
    except Exception as e:
        print(f"  (Note: could not load previous applications: {e})")
    return applied


def page_has_stop_signal(page) -> str | None:
    try:
        text = page.inner_text("body").lower()
        for phrase in STOP_PHRASES:
            if phrase in text:
                return phrase
        if "/checkpoint/" in page.url or "/uas/login" in page.url:
            return "session expired / checkpoint challenge"
    except Exception:
        pass
    return None


def passes_filters(card: dict, profile: Profile, role: str, already_applied: set = None) -> tuple[bool, str]:
    title = (card.get("title") or "").strip().lower()
    company = (card.get("company") or "").strip().lower()

    if already_applied and (title, company) in already_applied:
        return False, "already applied in previous run"

    exclude_kws = profile.data.get("title_exclude_keywords", [])
    for kw in exclude_kws:
        if kw.lower() in title:
            return False, f"title contains excluded seniority keyword ({kw})"

    required_keywords = profile.data.get("role_required_keywords", {}).get(role)
    if not required_keywords:
        generic = {"engineer", "developer", "administrator", "analyst", "senior", "junior", "lead"}
        required_keywords = [w for w in role.lower().split() if w not in generic]
    if required_keywords and not any(kw.lower() in title for kw in required_keywords):
        return False, f"title doesn't match role keywords ({role})"

    for excl in profile.company_exclude:
        if excl.lower() in company:
            return False, f"company excluded ({excl})"

    if profile.company_include_only:
        if not any(inc.lower() in company for inc in profile.company_include_only):
            return False, "not in include-only list"

    return True, ""


def dismiss_modal(page):
    """Safely closes any open Easy Apply dialog to prevent blocking subsequent clicks."""
    try:
        close_selectors = [
            '.jobs-easy-apply-modal button[aria-label="Dismiss"]',
            'button.artdeco-modal__dismiss',
            'button[aria-label="Dismiss"]',
            'button[aria-label="Close"]',
            'button[data-test-modal-close-btn]',
        ]
        for sel in close_selectors:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click()
                time.sleep(1)
                break

        discard_btn = page.locator(
            'button[data-control-name="discard_application_confirm_btn"], '
            'button.artdeco-modal__confirm-dialog-btn:has-text("Discard"), '
            'button:has-text("Discard")'
        ).first
        if discard_btn.is_visible(timeout=1500):
            discard_btn.click()
            time.sleep(1)
    except Exception:
        pass


def fill_text_field(page, field_id: str, text: str):
    page.evaluate(
        """([id, text]) => {
            const el = document.getElementById(id);
            if (!el) return false;
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(el, text);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
        }""",
        [field_id, text],
    )


def click_easy_apply_button(page) -> bool:
    """Finds and clicks the Easy Apply button on the job detail page."""
    selectors = [
        'button.jobs-apply-button',
        'div.jobs-apply-button--top-card button',
        'button[data-job-id].jobs-apply-button',
        '.jobs-s-apply button:has-text("Easy Apply")',
        'button:has-text("Easy Apply")',
    ]
    for sel in selectors:
        btn = page.locator(sel).first
        try:
            if btn.is_visible(timeout=1500):
                text = (btn.inner_text() or "").strip().lower()
                if "easy apply" in text:
                    btn.click()
                    return True
        except Exception:
            continue
    return False


def click_modal_button(page, target_text: str) -> bool:
    """Clicks a button with matching text inside the Easy Apply modal dialog."""
    return page.evaluate(
        """(target) => {
            const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
            if (!modal) return false;
            const btns = Array.from(modal.querySelectorAll('footer button, .artdeco-modal__actionbar button, button'));
            const targetLower = target.toLowerCase();
            const btn = btns.find(b => b.innerText.trim().toLowerCase() === targetLower);
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }""",
        target_text,
    )


def fill_form_step(page, profile: Profile, job_context: str, human_timeout: int = 120):
    """Fills fields in the current modal step (radio, select, text, checkboxes)."""
    answers = profile.answer_library()

    # 1. Handle radio buttons (e.g. Yes/No questions, authorizations)
    radio_groups = page.evaluate("""
        () => {
            const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
            if (!modal) return [];
            const groups = {};
            modal.querySelectorAll('input[type="radio"]').forEach(r => {
                const name = r.name;
                if (!name) return;
                if (!groups[name]) {
                    const fieldset = r.closest('fieldset');
                    const legend = fieldset ? fieldset.querySelector('legend')?.innerText?.trim() : '';
                    groups[name] = { question: legend || '', options: [], checked: false };
                }
                const labelEl = modal.querySelector(`label[for="${r.id}"]`) || r.closest('label');
                const labelText = labelEl ? labelEl.innerText.trim() : r.value;
                groups[name].options.push({ id: r.id, value: r.value, label: labelText, checked: r.checked });
                if (r.checked) groups[name].checked = true;
            });
            return Object.entries(groups).map(([name, data]) => ({ name, ...data }));
        }
    """)

    for group in radio_groups:
        if group.get("checked"):
            continue
        q = (group.get("question") or "").lower()
        options = group.get("options", [])
        if not options:
            continue

        target_label = "yes"
        if any(w in q for w in ["sponsorship", "require visa", "require immigration", "convicted", "felony"]):
            target_label = "no"

        stored = learned_answers.get_answer(q)
        if stored:
            target_label = stored.lower().strip()

        chosen = None
        for opt in options:
            if target_label in opt["label"].lower():
                chosen = opt
                break
        if not chosen and options:
            chosen = options[0]

        if chosen and chosen.get("id"):
            try:
                page.evaluate(f"""() => {{
                    const el = document.getElementById('{chosen["id"]}');
                    if (el) {{
                        el.click();
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}""")
            except Exception:
                pass

    # 2. Handle select dropdowns
    selects = page.evaluate("""
        () => {
            const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
            if (!modal) return [];
            return Array.from(modal.querySelectorAll('select')).map(s => {
                const lbl = modal.querySelector(`label[for="${s.id}"]`);
                return {
                    id: s.id,
                    label: lbl ? lbl.innerText.trim() : '',
                    value: s.value,
                    options: Array.from(s.options).map(o => ({ value: o.value, text: o.text.trim() }))
                };
            });
        }
    """)
    for sel in selects:
        if sel.get("value") and sel.get("value") not in ("Select an option", "0", ""):
            continue
        label = (sel.get("label") or "").lower()
        opts = sel.get("options", [])
        chosen_val = None

        if any(w in label for w in ["country", "phone", "code"]):
            for opt in opts:
                if "india" in opt["text"].lower() or "+91" in opt["text"]:
                    chosen_val = opt["value"]
                    break

        if not chosen_val and opts:
            for opt in opts:
                if opt["value"] and opt["text"].lower() not in ("select an option", "choose", "-"):
                    chosen_val = opt["value"]
                    break

        if chosen_val and sel.get("id"):
            try:
                page.select_option(f"#{sel['id']}", chosen_val)
            except Exception:
                pass

    # 3. Handle text and textarea inputs
    inputs = page.evaluate("""
        () => {
            const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
            if (!modal) return [];
            return Array.from(modal.querySelectorAll(
                'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="file"]), textarea'
            )).map(el => {
                let lbl = '';
                if (el.id) {
                    const l = modal.querySelector(`label[for="${el.id}"]`);
                    if (l) lbl = l.innerText.trim();
                }
                if (!lbl) {
                    lbl = el.getAttribute('aria-label') || el.placeholder || '';
                }
                return {
                    id: el.id,
                    tag: el.tagName,
                    type: el.type || '',
                    label: lbl,
                    value: el.value || '',
                };
            });
        }
    """)

    for inp in inputs:
        if inp.get("value"):
            continue
        label = (inp.get("label") or "").strip()
        label_lower = label.lower()
        if not label_lower:
            continue

        matched = None
        for key, val in answers.items():
            if key.replace("_", " ") in label_lower:
                matched = str(val)
                break

        if not matched:
            stored = learned_answers.get_answer(label_lower)
            if stored:
                matched = stored

        if not matched:
            if any(w in label_lower for w in ["how many years", "years of experience", "years of work experience"]):
                matched = "1"
                for skill in profile.skills_primary:
                    if skill.lower() in label_lower:
                        matched = "2"
                        break
            elif "gpa" in label_lower or "cgpa" in label_lower:
                matched = str(profile.data.get("cgpa", "7.53"))
            elif "ctc" in label_lower or "salary" in label_lower:
                matched = "6" if ("lakh" in label_lower or "lpa" in label_lower or inp.get("type") == "number") else "5 to 6 LPA"
            elif "notice period" in label_lower:
                matched = "0"
            elif "city" in label_lower or "location" in label_lower:
                matched = profile.current_city

        if not matched:
            draft = llm.draft_answer(label, profile.data, job_context)
            if draft and not draft.startswith("[NEEDS_HUMAN_INPUT"):
                matched = draft
            else:
                user_ans = ask_user(f"LinkedIn Easy Apply asks: '{label}'", timeout_seconds=human_timeout)
                if user_ans:
                    matched = user_ans
                    learned_answers.save_answer(label_lower, user_ans)
                else:
                    raise SkipJob(f"no answer for '{label}'")

        if matched and inp.get("id"):
            fill_text_field(page, inp["id"], str(matched))

    # 4. Handle required checkboxes
    checkboxes = page.evaluate("""
        () => {
            const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
            if (!modal) return [];
            return Array.from(modal.querySelectorAll('input[type="checkbox"]')).map(c => ({
                id: c.id,
                checked: c.checked,
                required: c.required
            }));
        }
    """)
    for cb in checkboxes:
        if not cb["checked"] and cb["required"] and cb["id"]:
            try:
                page.check(f"#{cb['id']}")
            except Exception:
                pass


def run_one_application(page, profile: Profile, job_title: str, company: str, human_timeout: int = 120) -> bool:
    """Executes a single Easy Apply flow. Returns True on success, raises SkipJob on failure."""
    job_context = f"{job_title} at {company}"

    if not click_easy_apply_button(page):
        raise SkipJob("no Easy Apply button")

    try:
        page.wait_for_selector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal', timeout=6000)
    except PWTimeout:
        raise SkipJob("Easy Apply modal did not open")

    time.sleep(1.2)

    try:
        for _ in range(10):
            stop = page_has_stop_signal(page)
            if stop:
                raise StopRun(f"stop signal mid-application: {stop}")

            fill_form_step(page, profile, job_context, human_timeout)
            time.sleep(0.8)

            btn_texts = page.evaluate("""
                () => {
                    const modal = document.querySelector('.jobs-easy-apply-modal, [role="dialog"], .artdeco-modal');
                    if (!modal) return [];
                    return Array.from(modal.querySelectorAll('footer button, .artdeco-modal__actionbar button, button'))
                      .map(b => b.innerText.trim().toLowerCase())
                      .filter(Boolean);
                }
            """)

            if "submit application" in btn_texts:
                click_modal_button(page, "Submit application")
                time.sleep(2.5)
                click_modal_button(page, "Done")
                dismiss_modal(page)
                return True
            elif "review" in btn_texts:
                click_modal_button(page, "Review")
            elif "next" in btn_texts:
                click_modal_button(page, "Next")
            else:
                raise SkipJob(f"unrecognized modal buttons: {btn_texts}")

            time.sleep(1.2)

        raise SkipJob("exceeded step cap without reaching submit")

    except SkipJob:
        dismiss_modal(page)
        raise
    except StopRun:
        dismiss_modal(page)
        raise
    except Exception as e:
        dismiss_modal(page)
        raise SkipJob(f"error during application: {e}")


def run():
    profile = Profile.load()
    if not Path(SESSION_FILE).exists():
        raise SystemExit(f"{SESSION_FILE} not found. Run: python login_capture.py linkedin")

    already_applied = load_already_applied()
    print(f"Loaded {len(already_applied)} previously applied jobs from log to prevent duplicates.")

    human_timeout = profile.data.get("human_input_timeout_seconds", 120)
    applied = 0

    with sync_playwright() as p:
        browser_mode = profile.data.get("browser_mode", "visible")
        extra_args = ["--disable-blink-features=AutomationControlled"]
        if browser_mode == "minimized":
            extra_args.append("--start-minimized")
        is_headless = (browser_mode == "headless")

        launch_kwargs = {
            "headless": is_headless,
            "slow_mo": 150,
            "ignore_default_args": ["--enable-automation"],
            "args": extra_args,
        }
        try:
            browser = p.chromium.launch(channel="chrome", **launch_kwargs)
        except Exception:
            browser = p.chromium.launch(**launch_kwargs)

        context = browser.new_context(
            storage_state=SESSION_FILE,
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

        # Check session validity
        print("Checking LinkedIn session...")
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)
        except Exception as e:
            print(f"  (Initial navigation notice: {e})")

        stop = page_has_stop_signal(page)
        if stop or "/login" in page.url or "/uas/" in page.url or "/checkpoint/" in page.url:
            print("\n" + "!" * 60)
            print("[ERROR] Your LinkedIn session is expired or not authenticated.")
            print("Please capture a fresh session by running:")
            print("    python login_capture.py linkedin")
            print("!" * 60 + "\n")
            browser.close()
            return

        print("LinkedIn session is active. Starting Easy Apply automation...")

        for role in profile.target_roles:
            if applied >= profile.stop_after_n_applications:
                break

            search_url = (
                f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(role)}"
                "&f_AL=true"
            )
            print(f"\n--- Searching LinkedIn: {role} ({search_url}) ---")
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2.5)
            except Exception as e:
                print(f"  (Search navigation error: {e})")
                continue

            stop = page_has_stop_signal(page)
            if stop:
                print(f"STOPPING: {stop}")
                log_row([datetime.now(), "linkedin", "-", "-", "stopped", stop])
                browser.close()
                return

            # Scroll list container to load lazy-loaded cards
            page.evaluate("""
                () => {
                    const el = document.querySelector('.jobs-search-results-list, .scaffold-layout__list');
                    if (el) el.scrollTop = el.scrollHeight;
                }
            """)
            time.sleep(1.5)

            cards = page.evaluate("""
                () => {
                    const items = document.querySelectorAll(
                        'li.jobs-search-results__list-item, div.job-card-container, [data-occludable-job-id]'
                    );
                    const out = [];
                    const seen = new Set();
                    items.forEach((c, idx) => {
                        const titleEl = c.querySelector(
                            'a.job-card-list__title, a.job-card-container__link, strong, [class*="job-card-list__title"]'
                        );
                        const compEl = c.querySelector(
                            '[class*="company-name"], .job-card-container__primary-description, [class*="primary-description"]'
                        );
                        const title = titleEl ? titleEl.innerText.trim() : '';
                        const company = compEl ? compEl.innerText.trim() : '';
                        if (title && !seen.has(title + company)) {
                            seen.add(title + company);
                            out.push({ idx, title, company });
                        }
                    });
                    return out;
                }
            """)
            print(f"Found {len(cards)} job cards for '{role}'.")

            card_locators = page.locator(
                'li.jobs-search-results__list-item, div.job-card-container, [data-occludable-job-id]'
            )

            for item in cards:
                if applied >= profile.stop_after_n_applications:
                    break

                title = item.get("title", "")
                company = item.get("company", "")

                ok, reason = passes_filters(item, profile, role, already_applied)
                if not ok:
                    log_row([datetime.now(), "linkedin", title, company, "skipped", reason])
                    print(f"Skipped: {title} @ {company} — {reason}")
                    continue

                try:
                    target_card = card_locators.nth(item["idx"])
                    target_card.scroll_into_view_if_needed()
                    target_card.click()
                    time.sleep(1.5)

                    success = run_one_application(page, profile, title, company, human_timeout)
                    if success:
                        applied += 1
                        already_applied.add((title.strip().lower(), company.strip().lower()))
                        log_row([datetime.now(), "linkedin", title, company, "applied", ""])
                        print(f"Applied: {title} @ {company} ({applied} total)")
                        time.sleep(profile.pace_seconds_between_actions)

                except SkipJob as e:
                    log_row([datetime.now(), "linkedin", title, company, "skipped", str(e)])
                    print(f"Skipped: {title} @ {company} — {e}")
                    continue
                except StopRun as e:
                    print(f"STOPPING: {e}")
                    log_row([datetime.now(), "linkedin", title, company, "stopped", str(e)])
                    browser.close()
                    return
                except Exception as e:
                    dismiss_modal(page)
                    log_row([datetime.now(), "linkedin", title, company, "skipped", f"unexpected error: {e}"])
                    print(f"Skipped: {title} @ {company} — unexpected error: {e}")
                    continue

        browser.close()

    print(f"\nDone. {applied} LinkedIn applications submitted this run. See {LOG_FILE} for details.")


if __name__ == "__main__":
    run()
