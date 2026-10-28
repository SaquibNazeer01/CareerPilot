# CareerPilot — AI-Powered Job Application Automation Studio

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Playwright-Automation-45ba4b?style=flat&logo=playwright&logoColor=white" alt="Playwright" />
  <img src="https://img.shields.io/badge/Flask-Web%20Studio-000000?style=flat&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/AI%20Screening-Gemini%20%26%20Groq-4285F4?style=flat&logo=google&logoColor=white" alt="LLM Engine" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" />
</p>

**CareerPilot** is an intelligent, high-efficiency job application automation studio designed for modern job seekers. It features a sleek, local web dashboard paired with autonomous browser automation engines for **Naukri.com** and **LinkedIn Easy Apply**, along with a profile visibility booster (Resume Refresher).

It combines real browser sessions with free-tier AI screening answer generation (Google Gemini & Groq fallback) to accurately handle multi-step applications using only verified facts from your personal profile.

---

## 👨‍💻 Developer Information

- **Developer:** **Saquib Nazeer**
- **Email:** [bhatsaakib505@gmail.com](mailto:bhatsaakib505@gmail.com)
- **Website / Portfolio:** [https://saquibb.me](https://saquibb.me)
- **GitHub:** [@SaquibNazeer01](https://github.com/SaquibNazeer01)

---

## ✨ Key Features

1. **Integrated Web Command Studio (`server.py` / `start_dashboard.bat`):**
   - Clean, modern dashboard to manage your resume, applicant profile, target roles, and API credentials in one place.
   - Configure details once — everything persists permanently on your machine in `profile.yaml`, `resume.pdf`, and `.env`.
   - Real-time live execution logs streamed directly into an embedded developer console.

2. **Autonomous Multi-Platform Support:**
   - **Naukri Auto-Apply (`naukri_apply.py`):** Automatically searches target roles, evaluates match criteria, skips duplicates, and answers recruiter questionnaires.
   - **LinkedIn Easy Apply (`linkedin_apply.py`):** Traverses multi-step easy-apply modals, fills contact info, and handles screening queries.
   - **Resume Refresher (`naukri_refresh_resume.py`):** Re-uploads your active resume with a single click or schedule to stamp your profile as "recently active" for top recruiter search placement.

3. **1-Click Cookie Connect & Anti-Bot Stealth:**
   - Fast session connection: simply paste your session cookie (`li_at` for LinkedIn or `AUTHTOKEN` for Naukri) to connect instantly without browser popups or CAPTCHA friction.
   - Built with anti-bot evasion techniques (`ignore_default_args=["--enable-automation"]`) to bypass detection flags.

4. **Hallucination-Free AI Screening Assistant:**
   - Answers employer screening questions strictly based on the experience, metrics, and skills listed in your profile.
   - Powered by Google Gemini (100% free) with automatic fallback to Groq.

5. **100% Privacy & Local Storage:**
   - No data or credentials are ever sent to third-party databases. All keys, resumes, and cookies remain exclusively on your local filesystem.

---

## 🚀 Quick Start (Web Dashboard)

The fastest and easiest way to use CareerPilot:

1. **Launch the Dashboard:**
   - On Windows, double-click **`start_dashboard.bat`** (or execute `python server.py`).
2. **Open the Studio:**
   - Navigate to **`http://127.0.0.1:5000`** in your browser.
3. **Set Up in 2 Minutes:**
   - Upload your active resume (`.pdf`).
   - Fill in your applicant details and target job titles.
   - Paste your free Gemini/Groq API keys and connect your platform session via 1-Click Cookie Connect.
4. **Launch Automation:**
   - Click **Start Naukri Automation** or **Start LinkedIn Automation** whenever you want to apply!

---

## 🛠️ Manual CLI Installation & Setup

If you prefer running via the command line:

### 1. Clone & Create Environment
```bash
git clone https://github.com/SaquibNazeer01/CareerPilot.git
cd CareerPilot

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Credentials (`.env`)
```bash
cp .env.example .env
```
Edit `.env` with your free AI keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```
- **Gemini Key (Free):** [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Groq Key (Free):** [https://console.groq.com/keys](https://console.groq.com/keys)

### 3. Configure Profile (`profile.yaml`)
```bash
cp profile.example.yaml profile.yaml
```
Fill in your experience, skills, target roles, notice period, and desired salary. Put your PDF resume in the root folder matching `resume_file_name`.

### 4. Connect Sessions
Run the interactive login capture tool:
```bash
python login_capture.py naukri
python login_capture.py linkedin
```
*(Or use the 1-Click Cookie Connect in the Web Dashboard)*.

### 5. Run Automations
```bash
# Run Naukri Job Applications
python naukri_apply.py

# Run LinkedIn Easy Apply
python linkedin_apply.py

# Refresh Resume on Naukri
python naukri_refresh_resume.py
```

---

## 📂 Project Architecture

```
CareerPilot/
├── server.py                 # Flask web backend & API controller
├── start_dashboard.bat       # 1-click Windows desktop dashboard launcher
├── static/                   # Modern Web Studio UI
│   ├── index.html            # Responsive single-page application
│   ├── style.css             # Obsidian modern design system
│   └── app.js                # Frontend state management & SSE live logs
├── naukri_apply.py           # Naukri automation pipeline & screening engine
├── linkedin_apply.py         # LinkedIn Easy Apply autonomous bot
├── naukri_refresh_resume.py  # Recruiter search ranking resume refresher
├── login_capture.py          # Session cookie capture & verification tool
├── profile.example.yaml      # Applicant profile template
├── .env.example              # Environment secret template
├── common/                   # Core shared utilities
│   ├── profile.py            # Profile parser and validator
│   ├── llm.py               # Multi-provider LLM dispatcher (Gemini & Groq)
│   ├── gemini.py             # Google Gemini client integration
│   ├── groq_llm.py           # Groq client integration
│   ├── human_input.py        # Terminal / web interactive fallback handler
│   └── learned_answers.py   # Screening question memory cache
└── requirements.txt          # Python dependencies
```

---

## ⚠️ Important Disclaimer & Terms of Use

- **Account Safety & Responsibility:** CareerPilot is developed for educational, productivity, and personal automation purposes. Automated actions can be against the terms of service of various platforms. The tool implements human-like pacing, stops immediately upon security checkpoints/CAPTCHAs, and avoids headless bot flags, but users assume full responsibility when applying to accounts.
- **Run from Residential IPs:** Datacenter / VPS IPs (AWS, GCP, Azure, Oracle Cloud) are blocked at the CDN level by Naukri. Always run CareerPilot on your local desktop, laptop, or residential network.

---

## 📜 License

Distributed under the **MIT License**. Free for personal and open-source use. See `LICENSE` for details.

---

<p align="center">
  Crafted with ❤️ by <a href="https://saquibb.me"><b>Saquib Nazeer</b></a>
</p>
