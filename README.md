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

## 📖 Complete Beginner's Guide (Step-by-Step Setup)

Anyone can set up and run CareerPilot in less than 5 minutes. No coding experience required!

### Step 1: Download & Install Requirements

1. **Install Python:**
   - If you don't already have Python installed, download it from [python.org](https://www.python.org/downloads/).
   - ⚠️ **Important during installation:** Make sure to check the box that says **"Add python.exe to PATH"**.

2. **Download CareerPilot:**
   - Click the green **Code** button at the top of this GitHub page and click **Download ZIP**.
   - Extract the downloaded ZIP file to any folder on your computer (e.g. `C:\CareerPilot`).
   - *(Or if you use Git, run `git clone https://github.com/SaquibNazeer01/CareerPilot.git`)*.

3. **Install Dependencies (One-time only):**
   - Open Command Prompt or PowerShell in the extracted folder and run:
     ```bash
     pip install -r requirements.txt
     playwright install chromium
     ```

---

### Step 2: Open the Web Studio

1. In the project folder, simply **double-click** the file named:
   ```text
   start_dashboard.bat
   ```
   *(Or open your terminal and type `python server.py`)*.
2. A browser window will automatically open with your personal dashboard at:
   ```text
   http://127.0.0.1:5000
   ```

---

### Step 3: Enter Your Details (Only Once!)

Your details are saved permanently on your computer in local files (`profile.yaml` and `.env`), so you only have to do this once:

1. **Upload Resume:** Click the upload box in **Tab 2 ("Active Resume")** and select your PDF resume.
2. **Fill Profile Details:** Go to **Tab 3 ("Applicant Dossier")** and enter your name, phone number, total years of experience, current salary, expected salary, and notice period.
3. **Set Target Job Roles:** In **Tab 4 ("Target Roles")**, enter the job titles you want to search and apply for (e.g., *"Frontend Developer"*, *"Python Developer"*, *"Full Stack Engineer"*).
4. **Get a Free AI Key (Optional but recommended):**
   - Click the free link in **Tab 5 ("API Credentials")** to get a Google Gemini API key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
   - Paste the key and click **Save API Keys**. This allows the tool to answer recruiter screening questions (e.g., *"Why do you want to work with us?"*) accurately using facts from your profile.

---

### Step 4: Connect Your Account (1-Click Cookie Connect)

You don't need to type passwords or solve CAPTCHAs. Since you are already logged in to LinkedIn or Naukri on your normal browser:

#### For LinkedIn:
1. Open the browser tab where you are logged into **LinkedIn**.
2. Press <kbd>F12</kbd> (or Right-Click ➔ **Inspect**).
3. At the top, click the **Application** tab *(in Firefox, click **Storage**)*.
4. On the left sidebar under **Cookies**, click `https://www.linkedin.com`.
5. Find the row named **`li_at`**, double-click its value, and copy it (<kbd>Ctrl</kbd> + <kbd>C</kbd>).
6. In CareerPilot Studio ➔ **Tab 5 ("API Credentials & Sessions")**, paste the value into the **LinkedIn Cookie** box and click **Connect Cookie**.

#### For Naukri:
1. Open your logged-in **Naukri** tab in your browser.
2. Press <kbd>F12</kbd> ➔ **Application** ➔ **Cookies** ➔ `https://www.naukri.com`.
3. Find **`AUTHTOKEN`**, copy its value, and paste it into the **Naukri Cookie** box in Tab 5.

*Your session status will immediately turn green (**● Session Active**)!*

---

### Step 5: Start Applying!

Whenever you want to apply for jobs:

1. Go to **Tab 1 ("Command Center")**.
2. Click **Launch Naukri Automation** or **Launch LinkedIn Automation**.
3. Watch the live terminal apply to matching jobs for you automatically, skipping duplicate listings and answering screening questions based on your profile!
4. **Bonus — Resume Refresher:** Click **"Refresh Resume Now"** anytime to automatically remove and re-upload your resume on Naukri, keeping your profile at the top of recruiter searches!

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
