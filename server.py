"""
Job Apply Automation - Web Dashboard & Control Server
Provides a modern web interface for managing profiles, uploading resumes,
monitoring sessions, reviewing application logs, and launching automations.
"""

import os
import sys
import json
import csv
import queue
import signal
import psutil
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for UTF-8 characters
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from flask import Flask, request, jsonify, Response, send_file, send_from_directory
from werkzeug.utils import secure_filename
import yaml

BASE_DIR = Path(__file__).resolve().parent
PROFILE_PATH = BASE_DIR / "profile.yaml"
EXAMPLE_PROFILE_PATH = BASE_DIR / "profile.example.yaml"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
LOG_PATH = BASE_DIR / "applications_log.csv"
LEARNED_ANSWERS_PATH = BASE_DIR / "learned_answers.json"
NAUKRI_SESSION_PATH = BASE_DIR / "session_naukri.json"
LINKEDIN_SESSION_PATH = BASE_DIR / "session_linkedin.json"

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload

# Global process management
process_lock = threading.Lock()
current_process = None
current_process_name = None
log_history = []
MAX_HISTORY_LINES = 2000
log_subscribers = []


def add_log_line(line: str):
    """Adds a log line to history and notifies all SSE subscribers."""
    global log_history
    with process_lock:
        log_history.append(line)
        if len(log_history) > MAX_HISTORY_LINES:
            log_history = log_history[-MAX_HISTORY_LINES:]

    # Notify all active SSE queues
    dead_subscribers = []
    for q in log_subscribers:
        try:
            q.put_nowait(line)
        except Exception:
            dead_subscribers.append(q)

    for dead in dead_subscribers:
        if dead in log_subscribers:
            log_subscribers.remove(dead)


def stream_reader(proc, proc_name):
    """Background thread to read process stdout and stderr."""
    global current_process, current_process_name
    add_log_line(f"🚀 [{proc_name}] Automation started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        for raw_line in iter(proc.stdout.readline, ""):
            if not raw_line:
                break
            line = raw_line.rstrip("\r\n")
            add_log_line(line)
    except Exception as e:
        add_log_line(f"⚠️ Error reading process stream: {e}")
    finally:
        proc.stdout.close()
        proc.wait()
        exit_code = proc.returncode
        with process_lock:
            if current_process == proc:
                current_process = None
                current_process_name = None
        status_msg = "Completed successfully" if exit_code == 0 else f"Terminated with exit code {exit_code}"
        add_log_line(f"🏁 [{proc_name}] {status_msg} at {datetime.now().strftime('%H:%M:%S')}")


def get_profile_data() -> dict:
    """Reads profile.yaml or falls back to profile.example.yaml."""
    target_path = PROFILE_PATH if PROFILE_PATH.exists() else EXAMPLE_PROFILE_PATH
    if not target_path.exists():
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data
    except Exception as e:
        return {"error": str(e)}


def save_profile_data(data: dict) -> None:
    """Safely saves data to profile.yaml."""
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)


def get_env_data() -> dict:
    """Reads .env or .env.example."""
    target_path = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    env_vars = {}
    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def is_valid_linkedin_session() -> bool:
    """Checks if session_linkedin.json exists and contains a valid li_at authentication cookie."""
    if not LINKEDIN_SESSION_PATH.exists():
        return False
    try:
        with open(LINKEDIN_SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            cookies = data.get("cookies", [])
            return any(c.get("name") == "li_at" and len(c.get("value", "")) > 10 for c in cookies)
    except Exception:
        return False


def is_valid_naukri_session() -> bool:
    """Checks if session_naukri.json exists and contains valid authentication cookies."""
    if not NAUKRI_SESSION_PATH.exists():
        return False
    try:
        with open(NAUKRI_SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            cookies = data.get("cookies", [])
            return len(cookies) > 0 and any(
                c.get("name") in ["AUTHTOKEN", "NUKL", "nauk_att", "naukri_user_id"]
                or "naukri" in c.get("domain", "")
                for c in cookies
            )
    except Exception:
        return False


def save_env_data(data: dict) -> None:
    """Saves API keys and platform credentials to .env while preserving existing ones."""
    current = get_env_data()
    allowed_keys = (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "LINKEDIN_USERNAME",
        "LINKEDIN_PASSWORD",
        "NAUKRI_USERNAME",
        "NAUKRI_PASSWORD",
    )
    for k in allowed_keys:
        if k in data:
            val = str(data[k]).strip()
            # If password field is blank on save, keep current password
            if "PASSWORD" in k and val == "" and current.get(k):
                continue
            current[k] = val

    lines = ["# Auto-generated secrets configuration"]
    for k, v in current.items():
        if k in allowed_keys and v:
            lines.append(f"{k}={v}")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")



@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns overview of system readiness."""
    profile_exists = PROFILE_PATH.exists()
    profile = get_profile_data()
    resume_name = profile.get("resume_file_name", "resume.pdf") if isinstance(profile, dict) else "resume.pdf"
    resume_path = BASE_DIR / resume_name
    resume_exists = resume_path.exists() and resume_path.is_file()

    resume_info = None
    if resume_exists:
        stat = resume_path.stat()
        resume_info = {
            "name": resume_name,
            "size": stat.st_size,
            "size_formatted": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.2f} MB",
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }

    env_data = get_env_data()
    gemini_key = env_data.get("GEMINI_API_KEY", "")
    groq_key = env_data.get("GROQ_API_KEY", "")

    # Validate profile completeness
    blocking_fields = [
        "total_experience_years",
        "notice_period_days",
        "current_ctc_lpa",
        "expected_ctc_lpa",
        "resume_file_name",
        "candidate_name",
        "email",
        "phone",
        "target_roles"
    ]
    missing_fields = []
    if isinstance(profile, dict):
        for f in blocking_fields:
            val = profile.get(f)
            if val is None or val == "" or (isinstance(val, list) and len(val) == 0):
                missing_fields.append(f)

    with process_lock:
        is_running = current_process is not None and current_process.poll() is None
        running_name = current_process_name if is_running else None

    return jsonify({
        "profile_exists": profile_exists,
        "profile_valid": profile_exists and len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "resume_exists": resume_exists,
        "resume_info": resume_info,
        "naukri_session_exists": is_valid_naukri_session(),
        "linkedin_session_exists": is_valid_linkedin_session(),
        "has_naukri_creds": bool(env_data.get("NAUKRI_USERNAME") and env_data.get("NAUKRI_PASSWORD")),
        "has_linkedin_creds": bool(env_data.get("LINKEDIN_USERNAME") and env_data.get("LINKEDIN_PASSWORD")),
        "has_gemini_key": bool(gemini_key and "your-" not in gemini_key),
        "has_groq_key": bool(groq_key and "your-" not in groq_key),
        "is_running": is_running,
        "running_name": running_name,
    })


@app.route("/api/profile", methods=["GET", "POST"])
def api_profile():
    if request.method == "GET":
        data = get_profile_data()
        return jsonify({
            "is_saved": PROFILE_PATH.exists(),
            "profile": data
        })

    # POST - update profile
    req_data = request.json or {}
    save_profile_data(req_data)
    return jsonify({"success": True, "message": "Profile details saved successfully!"})


@app.route("/api/upload-resume", methods=["POST"])
def api_upload_resume():
    """Uploads a resume file and saves it in the project root."""
    if "resume" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        return jsonify({"error": "Only PDF or Word documents (.pdf, .docx, .doc) are supported"}), 400

    filename = secure_filename(file.filename) or "resume.pdf"
    save_path = BASE_DIR / filename
    file.save(save_path)

    # Automatically update resume_file_name in profile.yaml
    profile_data = get_profile_data()
    profile_data["resume_file_name"] = filename
    save_profile_data(profile_data)

    stat = save_path.stat()
    return jsonify({
        "success": True,
        "message": f"Resume '{filename}' uploaded and saved successfully!",
        "filename": filename,
        "size": stat.st_size,
        "size_formatted": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.2f} MB",
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/api/resume/download", methods=["GET"])
def api_resume_download():
    """Download current active resume file."""
    profile = get_profile_data()
    filename = profile.get("resume_file_name", "resume.pdf") if isinstance(profile, dict) else "resume.pdf"
    path = BASE_DIR / filename
    if not path.exists():
        return jsonify({"error": f"Resume '{filename}' not found on server."}), 404
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/api/env", methods=["GET", "POST"])
def api_env():
    if request.method == "GET":
        env_vars = get_env_data()
        return jsonify({
            "has_env": ENV_PATH.exists(),
            "gemini_api_key": env_vars.get("GEMINI_API_KEY", ""),
            "groq_api_key": env_vars.get("GROQ_API_KEY", ""),
            "linkedin_username": env_vars.get("LINKEDIN_USERNAME", ""),
            "has_linkedin_password": bool(env_vars.get("LINKEDIN_PASSWORD")),
            "naukri_username": env_vars.get("NAUKRI_USERNAME", ""),
            "has_naukri_password": bool(env_vars.get("NAUKRI_PASSWORD")),
        })

    # POST - update API keys and platform credentials
    data = request.json or {}
    save_env_data(data)
    return jsonify({"success": True, "message": "Credentials saved to .env successfully!"})


def build_storage_state_from_text(platform: str, raw_text: str) -> dict:
    raw = (raw_text or "").strip()
    cookies = []
    domain = ".linkedin.com" if platform == "linkedin" else ".naukri.com"

    # Case 1: JSON array format (from browser extensions like EditThisCookie)
    if raw.startswith("[") and raw.endswith("]"):
        try:
            arr = json.loads(raw)
            for item in arr:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies.append({
                        "name": str(item["name"]).strip(),
                        "value": str(item["value"]).strip(),
                        "domain": item.get("domain", domain),
                        "path": item.get("path", "/"),
                        "expires": int(item.get("expirationDate") or item.get("expires") or (time.time() + 31536000)),
                        "httpOnly": bool(item.get("httpOnly", False)),
                        "secure": bool(item.get("secure", True)),
                        "sameSite": "None" if item.get("sameSite") in ["None", "no_restriction"] else "Lax"
                    })
        except Exception:
            pass

    # Case 2: Cookie header string ("name=val; name2=val2")
    if not cookies and "=" in raw:
        parts = raw.split(";")
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v:
                    cookies.append({
                        "name": k,
                        "value": v,
                        "domain": domain,
                        "path": "/",
                        "expires": int(time.time() + 31536000),
                        "httpOnly": False,
                        "secure": True,
                        "sameSite": "Lax"
                    })

    # Case 3: Raw token string (e.g. li_at for LinkedIn or AUTHTOKEN for Naukri)
    if not cookies and len(raw) > 10 and "=" not in raw:
        cookie_name = "li_at" if platform == "linkedin" else "AUTHTOKEN"
        cookies.append({
            "name": cookie_name,
            "value": raw,
            "domain": domain,
            "path": "/",
            "expires": int(time.time() + 31536000),
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        })
        cookies.append({
            "name": cookie_name,
            "value": raw,
            "domain": f".www{domain}",
            "path": "/",
            "expires": int(time.time() + 31536000),
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        })

    return {"cookies": cookies, "origins": []}


@app.route("/api/session/cookie-connect", methods=["POST"])
def api_session_cookie_connect():
    """Allows 1-click connecting via pasted browser session token or cookie string."""
    data = request.json or {}
    platform = (data.get("platform") or "").lower().strip()
    cookie_text = (data.get("cookie_text") or "").strip()

    if platform not in ["linkedin", "naukri"]:
        return jsonify({"error": "Invalid platform. Must be 'linkedin' or 'naukri'."}), 400
    if not cookie_text:
        return jsonify({"error": "Please enter a cookie token or cookie string."}), 400

    state = build_storage_state_from_text(platform, cookie_text)
    if not state.get("cookies"):
        return jsonify({"error": "Could not parse any valid cookies from the provided text."}), 400

    target_path = LINKEDIN_SESSION_PATH if platform == "linkedin" else NAUKRI_SESSION_PATH
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        valid = is_valid_linkedin_session() if platform == "linkedin" else is_valid_naukri_session()
        add_log_line(f"🍪 [{platform.upper()} Cookie Connect] Saved {len(state['cookies'])} session cookies to {target_path.name}")
        return jsonify({
            "success": True,
            "message": f"Successfully connected {platform.title()} session with {len(state['cookies'])} cookies!",
            "is_valid": valid,
            "cookies_count": len(state["cookies"])
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save session file: {str(e)}"}), 500


@app.route("/api/logs", methods=["GET"])
def api_logs():
    """Reads applications_log.csv and calculates summary stats."""
    if not LOG_PATH.exists():
        return jsonify({
            "exists": False,
            "total": 0,
            "applied": 0,
            "skipped": 0,
            "stopped": 0,
            "rows": []
        })

    rows = []
    total = 0
    applied = 0
    skipped = 0
    stopped = 0

    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                status = (row.get("status") or "").lower()
                if "applied" in status or status == "applied":
                    applied += 1
                elif "skip" in status or status == "skipped":
                    skipped += 1
                elif "stop" in status or status == "stopped" or "error" in status:
                    stopped += 1
                rows.append(row)
    except Exception as e:
        return jsonify({"error": str(e), "rows": []})

    # Return most recent first
    rows.reverse()

    return jsonify({
        "exists": True,
        "total": total,
        "applied": applied,
        "skipped": skipped,
        "stopped": stopped,
        "rows": rows[:100]  # top 100 for fast UI loading
    })


@app.route("/api/learned-answers", methods=["GET", "POST", "DELETE"])
def api_learned_answers():
    answers = {}
    if LEARNED_ANSWERS_PATH.exists():
        try:
            with open(LEARNED_ANSWERS_PATH, "r", encoding="utf-8") as f:
                answers = json.load(f)
        except Exception:
            answers = {}

    if request.method == "GET":
        return jsonify({"answers": answers})

    if request.method == "POST":
        data = request.json or {}
        q = (data.get("question") or "").strip()
        ans = (data.get("answer") or "").strip()
        if not q:
            return jsonify({"error": "Question is required"}), 400
        answers[q] = ans
        with open(LEARNED_ANSWERS_PATH, "w", encoding="utf-8") as f:
            json.dump(answers, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "message": "Answer saved"})

    if request.method == "DELETE":
        data = request.json or {}
        q = data.get("question")
        if q and q in answers:
            del answers[q]
            with open(LEARNED_ANSWERS_PATH, "w", encoding="utf-8") as f:
                json.dump(answers, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "message": "Answer deleted"})


def get_python_executable() -> str:
    """Finds the best python executable that has playwright and dependencies installed."""
    candidates = [
        sys.executable,
        r"C:\Program Files\Python312\python.exe",
        r"C:\Users\bhats\anaconda3\python.exe",
        shutil.which("python"),
        shutil.which("python3")
    ]
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return sys.executable


@app.route("/api/automation/start", methods=["POST"])
def api_automation_start():
    """Starts an automation task."""
    global current_process, current_process_name

    data = request.json or {}
    action = data.get("action")

    with process_lock:
        if current_process is not None and current_process.poll() is None:
            return jsonify({
                "error": f"Automation '{current_process_name}' is already running. Please stop it first."
            }), 400

    py_exec = get_python_executable()
    commands = {
        "naukri": [py_exec, "-u", "naukri_apply.py"],
        "linkedin": [py_exec, "-u", "linkedin_apply.py"],
        "refresh_resume": [py_exec, "-u", "naukri_refresh_resume.py"],
        "login_naukri": [py_exec, "-u", "login_capture.py", "naukri"],
        "login_linkedin": [py_exec, "-u", "login_capture.py", "linkedin"],
    }

    if action not in commands:
        return jsonify({"error": f"Unknown automation action: {action}"}), 400

    cmd = commands[action]
    action_labels = {
        "naukri": "Naukri Auto-Apply",
        "linkedin": "LinkedIn Easy-Apply",
        "refresh_resume": "Resume Refresh",
        "login_naukri": "Naukri Login Capture",
        "login_linkedin": "LinkedIn Login Capture",
    }
    label = action_labels[action]

    # Pre-checks
    if action in ["naukri", "refresh_resume"]:
        if not is_valid_naukri_session() and "login" not in action:
            return jsonify({
                "warning": "Naukri session not found or unauthenticated. Please click 'Connect Naukri' or 'Capture Session' first to log in."
            }), 400
    elif action == "linkedin":
        if not is_valid_linkedin_session():
            return jsonify({
                "warning": "LinkedIn session not found or unauthenticated. Please click 'Connect LinkedIn' or 'Capture Session' first to log in."
            }), 400

    try:
        # Start subprocess with unbuffered pipe, UTF-8 encoding, and environment credentials
        env_vars = get_env_data()
        sub_env = {
            **os.environ,
            **env_vars,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=sub_env
        )

        with process_lock:
            current_process = proc
            current_process_name = label

        # Start streaming reader thread
        t = threading.Thread(target=stream_reader, args=(proc, label), daemon=True)
        t.start()

        return jsonify({
            "success": True,
            "message": f"Started {label}",
            "process_name": label
        })
    except Exception as e:
        return jsonify({"error": f"Failed to start automation: {str(e)}"}), 500


@app.route("/api/automation/stop", methods=["POST"])
def api_automation_stop():
    """Stops the active automation task and its process tree."""
    global current_process, current_process_name
    with process_lock:
        if current_process is None or current_process.poll() is not None:
            return jsonify({"message": "No automation is currently running."})

        proc = current_process
        proc_name = current_process_name

    try:
        # Kill child processes if any (playwright/chromium)
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass

    add_log_line(f"🛑 [{proc_name}] Automation stopped by user.")
    with process_lock:
        current_process = None
        current_process_name = None

    return jsonify({"success": True, "message": "Automation stopped."})


@app.route("/api/automation/input", methods=["POST"])
def api_automation_input():
    """Sends user response/input to the running process's stdin."""
    global current_process
    data = request.json or {}
    text = data.get("text", "")

    with process_lock:
        if current_process is None or current_process.poll() is not None:
            return jsonify({"error": "No running automation to send input to."}), 400
        proc = current_process

    try:
        proc.stdin.write(text + "\n")
        proc.stdin.flush()
        add_log_line(f"👤 [User Input]: {text}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Failed to send input: {str(e)}"}), 500


@app.route("/api/automation/stream")
def api_automation_stream():
    """Server-Sent Events (SSE) streaming real-time console logs."""
    q = queue.Queue(maxsize=1000)
    with process_lock:
        log_subscribers.append(q)
        # Pre-populate subscriber with last 40 lines of recent history
        recent = list(log_history[-40:])

    for line in recent:
        q.put(line)

    def event_stream():
        try:
            while True:
                try:
                    line = q.get(timeout=20)
                    yield f"data: {json.dumps({'line': line})}\n\n"
                except queue.Empty:
                    # Keep-alive ping
                    yield f": keep-alive\n\n"
        except GeneratorExit:
            with process_lock:
                if q in log_subscribers:
                    log_subscribers.remove(q)

    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n=======================================================")
    print(f"[*] AutoApply Studio Dashboard running at:")
    print(f"[*] http://127.0.0.1:{port}")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
