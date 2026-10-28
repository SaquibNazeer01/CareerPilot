/**
 * CareerPilot — Automated Career Assistant
 * Client Application Logic
 */

// Global State
let currentProfile = {};
let allLogs = [];
let currentFilter = 'all';
let isRunning = false;
let sseSource = null;

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initDragAndDrop();
  initShortcuts();
  initSSE();

  // Load initial data
  refreshSystemStatus();
  loadProfileData();
  loadEnvKeys();
  loadApplicationLogs();
  initInputListeners();

  // Background refresh every 6s
  setInterval(refreshSystemStatus, 6000);
});

function initInputListeners() {
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('input', () => markUnsaved());
    el.addEventListener('change', () => markUnsaved());
  });
}

function markUnsaved() {
  const el = document.getElementById('save-status-indicator');
  if (el) {
    el.textContent = '● Unsaved changes';
    el.style.color = '#b45309';
  }
}

function markSaved() {
  const el = document.getElementById('save-status-indicator');
  if (el) {
    el.textContent = '✓ All changes saved';
    el.style.color = '#047857';
  }
}

function addRoleTag(role) {
  const input = document.getElementById('prof-target-roles');
  if (!input) return;
  let list = (input.value || '').split(',').map(s => s.trim()).filter(Boolean);
  if (!list.includes(role)) {
    list.push(role);
    input.value = list.join(', ');
    showToast(`Added role: "${role}"`, 'info');
    markUnsaved();
  }
}

/* ===================================================================
   Tab Navigation
   =================================================================== */
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.getAttribute('data-tab');
      switchTab(targetId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  const activeBtn = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
  const activePane = document.getElementById(tabId);

  if (activeBtn) activeBtn.classList.add('active');
  if (activePane) activePane.classList.add('active');
}

/* ===================================================================
   System Status & Checklist
   =================================================================== */
async function refreshSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    const chip = document.getElementById('system-status-chip');
    const resumePill = document.getElementById('nav-resume-pill');

    const cardProfile = document.getElementById('step-card-profile');
    const badgeProfile = document.getElementById('step-badge-profile');
    const subProfile = document.getElementById('step-sub-profile');

    const cardResume = document.getElementById('step-card-resume');
    const badgeResume = document.getElementById('step-badge-resume');
    const subResume = document.getElementById('step-sub-resume');

    const cardRoles = document.getElementById('step-card-roles');
    const badgeRoles = document.getElementById('step-badge-roles');

    const cardKeys = document.getElementById('step-card-keys');
    const badgeKeys = document.getElementById('step-badge-keys');

    // 1. Profile Status
    if (data.profile_exists && data.profile_valid) {
      cardProfile.className = 'milestone-card completed';
      badgeProfile.className = 'milestone-status ready';
      badgeProfile.textContent = 'Saved';
      subProfile.textContent = 'Candidate info permanently stored';
    } else if (data.profile_exists) {
      cardProfile.className = 'milestone-card';
      badgeProfile.className = 'milestone-status';
      badgeProfile.textContent = 'Incomplete';
      subProfile.textContent = `Missing: ${data.missing_fields.slice(0, 2).join(', ')}`;
    } else {
      cardProfile.className = 'milestone-card';
      badgeProfile.className = 'milestone-status';
      badgeProfile.textContent = 'Fill Details';
      subProfile.textContent = 'Not configured yet';
    }

    // 2. Resume Status
    const activeFilename = document.getElementById('active-resume-filename');
    const activeSize = document.getElementById('active-resume-size');
    const activeDate = document.getElementById('active-resume-date');
    const resumeStatusBadge = document.getElementById('resume-badge-status');
    const btnDownload = document.getElementById('btn-download-resume');

    if (data.resume_exists && data.resume_info) {
      cardResume.className = 'milestone-card completed';
      badgeResume.className = 'milestone-status ready';
      badgeResume.textContent = 'Uploaded';
      subResume.textContent = `${data.resume_info.name} (${data.resume_info.size_formatted})`;

      resumePill.className = 'tab-badge ready';
      resumePill.textContent = 'Ready';

      resumeStatusBadge.textContent = 'Stored on Disk';
      resumeStatusBadge.className = 'badge-tag success';

      activeFilename.textContent = data.resume_info.name;
      activeSize.textContent = data.resume_info.size_formatted;
      activeDate.textContent = `Saved: ${data.resume_info.modified}`;
      btnDownload.style.display = 'inline-flex';
    } else {
      cardResume.className = 'milestone-card';
      badgeResume.className = 'milestone-status';
      badgeResume.textContent = 'Upload File';
      subResume.textContent = 'Upload PDF/Word document';

      resumePill.className = 'tab-badge';
      resumePill.textContent = 'Pending';

      resumeStatusBadge.textContent = 'Not Found';
      resumeStatusBadge.className = 'badge-tag';

      activeFilename.textContent = 'No resume uploaded yet';
      activeSize.textContent = '0 KB';
      activeDate.textContent = 'Please upload on the right';
      btnDownload.style.display = 'none';
    }

    // 3. Roles Status
    const hasRoles = data.profile_exists && !data.missing_fields.includes('target_roles');
    if (hasRoles) {
      cardRoles.className = 'milestone-card completed';
      badgeRoles.className = 'milestone-status ready';
      badgeRoles.textContent = 'Configured';
    } else {
      cardRoles.className = 'milestone-card';
      badgeRoles.className = 'milestone-status';
      badgeRoles.textContent = 'Set Roles';
    }

    // 4. AI Keys & Session
    const badgeNaukri = document.getElementById('badge-naukri-session');
    const badgeLinkedIn = document.getElementById('badge-linkedin-session');
    const naukriSublink = document.getElementById('naukri-session-sublink');
    const linkedinSublink = document.getElementById('linkedin-session-sublink');

    if (badgeNaukri) {
      if (data.naukri_session_exists) {
        badgeNaukri.className = 'session-pill active';
        badgeNaukri.textContent = '● Session Active';
      } else {
        badgeNaukri.className = 'session-pill';
        badgeNaukri.textContent = data.has_naukri_creds ? '○ Login Required' : '○ Not Connected';
      }
    }

    if (badgeLinkedIn) {
      if (data.linkedin_session_exists) {
        badgeLinkedIn.className = 'session-pill active';
        badgeLinkedIn.textContent = '● Session Active';
      } else {
        badgeLinkedIn.className = 'session-pill';
        badgeLinkedIn.textContent = data.has_linkedin_creds ? '○ Login Required' : '○ Not Connected';
      }
    }

    if (naukriSublink) {
      if (data.naukri_session_exists) {
        naukriSublink.innerHTML = `<span style="color: #059669; font-weight: 600;">✓ Naukri Session Active</span>`;
      } else {
        naukriSublink.innerHTML = `<a href="javascript:void(0)" onclick="switchTab('tab-credentials')" style="color: #4f46e5; text-decoration: none; font-weight: 600;">⚠️ Naukri Session Needed — Connect Now ↗</a>`;
      }
    }

    if (linkedinSublink) {
      if (data.linkedin_session_exists) {
        linkedinSublink.innerHTML = `<span style="color: #059669; font-weight: 600;">✓ LinkedIn Session Active</span>`;
      } else {
        linkedinSublink.innerHTML = `<a href="javascript:void(0)" onclick="switchTab('tab-credentials')" style="color: #0284c7; text-decoration: none; font-weight: 600;">⚠️ LinkedIn Session Needed — Connect Now ↗</a>`;
      }
    }

    if (data.has_gemini_key) {
      cardKeys.className = 'milestone-card completed';
      badgeKeys.className = 'milestone-status ready';
      badgeKeys.textContent = 'API Ready';
    } else {
      cardKeys.className = 'milestone-card';
      badgeKeys.className = 'milestone-status';
      badgeKeys.textContent = 'Key Needed';
    }

    // Progress Calculation
    let stepsDone = 0;
    if (data.profile_exists && data.profile_valid) stepsDone++;
    if (data.resume_exists) stepsDone++;
    if (hasRoles) stepsDone++;
    if (data.has_gemini_key) stepsDone++;

    const progressFraction = document.getElementById('progress-fraction');
    const progressBarFill = document.getElementById('progress-bar-fill');
    if (progressFraction) progressFraction.textContent = `${stepsDone} of 4 Steps Complete`;
    if (progressBarFill) progressBarFill.style.width = `${Math.max(10, (stepsDone / 4) * 100)}%`;

    // Overall Status Chip & Banner
    const setupCard = document.getElementById('setup-status-card');
    const setupHeading = document.getElementById('setup-heading');
    const setupP = document.getElementById('setup-paragraph');

    if (data.is_running) {
      chip.className = 'status-chip running';
      chip.innerHTML = `<span class="chip-dot"></span><span class="chip-text">Running: ${escapeHtml(data.running_name || 'Automation')}</span>`;
      setupHeading.textContent = 'Automation Currently Running';
      setupP.textContent = `${data.running_name} is processing applications. View the live activity log below.`;
    } else if (data.profile_valid && data.resume_exists && data.has_gemini_key) {
      chip.className = 'status-chip ready';
      chip.innerHTML = `<span class="chip-dot"></span><span class="chip-text">100% Ready to Apply</span>`;
      setupHeading.textContent = 'Your Details Are Saved & Ready';
      setupP.textContent = 'Your profile, resume, and credentials are permanently stored. Click "Launch Naukri Automation" or "Launch LinkedIn Automation" below anytime.';
    } else {
      chip.className = 'status-chip';
      chip.innerHTML = `<span class="chip-dot"></span><span class="chip-text">Setup in Progress</span>`;
      setupHeading.textContent = 'Complete Initial Setup (Only Once)';
      setupP.textContent = 'Please fill your applicant details and upload your resume once. Everything will be saved permanently so you can apply anytime with a single click.';
    }

    updateConsoleRunningState(data.is_running, data.running_name);

  } catch (err) {
    console.warn('Status check failed:', err);
  }
}

function updateConsoleRunningState(running, name) {
  isRunning = running;
  const dot = document.getElementById('console-live-dot');
  const txt = document.getElementById('console-status-text');
  const btnStop = document.getElementById('btn-stop-proc');
  const btnSaveSession = document.getElementById('btn-save-session-now');

  if (running) {
    if (dot) dot.className = 'pulse-indicator running';
    if (txt) {
      txt.className = 'console-badge running';
      txt.textContent = `Running: ${name || 'Task'}`;
    }
    if (btnStop) btnStop.style.display = 'inline-flex';
    if (btnSaveSession) {
      const isLogin = (name || '').toLowerCase().includes('login');
      btnSaveSession.style.display = isLogin ? 'inline-flex' : 'none';
    }
  } else {
    if (dot) dot.className = 'pulse-indicator';
    if (txt) {
      txt.className = 'console-badge';
      txt.textContent = 'Idle';
    }
    if (btnStop) btnStop.style.display = 'none';
    if (btnSaveSession) btnSaveSession.style.display = 'none';
  }
}

async function sendSaveSessionInput() {
  appendLog('👤 Confirmation sent: Saving session...', 'system');
  try {
    const res = await fetch('/api/automation/input', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: '' })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Session capture signal sent! Check terminal output.', 'success');
    } else {
      showToast(data.error || 'Failed to send signal', 'error');
    }
  } catch (err) {
    showToast('Failed to send confirmation: ' + err.message, 'error');
  }
}

/* ===================================================================
   Applicant Profile Management
   =================================================================== */
async function loadProfileData() {
  try {
    const res = await fetch('/api/profile');
    const json = await res.json();
    const p = json.profile || {};
    currentProfile = p;

    // Contact
    setVal('prof-name', p.candidate_name);
    setVal('prof-email', p.email);
    setVal('prof-phone', p.phone);
    setVal('prof-city', p.current_city);
    setVal('prof-relocate', Array.isArray(p.relocate_cities) ? p.relocate_cities.join(', ') : '');

    // Experience
    setVal('prof-exp', p.total_experience_years);
    setVal('prof-notice', p.notice_period_days);
    setCheck('prof-immediate', p.immediately_available);
    setCheck('prof-night', p.night_shift_ok);
    setCheck('prof-weekend', p.weekend_ok);

    // Compensation
    setVal('prof-cur-ctc', p.current_ctc_lpa);
    setVal('prof-exp-ctc', p.expected_ctc_lpa);
    setVal('prof-exp-text', p.expected_ctc_text || 'Negotiable');
    setVal('prof-policy', p.ctc_disclosure_policy || 'negotiable');

    // Education
    setVal('prof-highest-qual', p.highest_qualification);
    setVal('prof-degree', p.degree);
    setVal('prof-college', p.college);
    setVal('prof-cgpa', p.cgpa);
    setVal('prof-linkedin', p.linkedin_url);
    setVal('prof-github', p.github_url);

    // Target Roles & Filters
    setVal('prof-target-roles', Array.isArray(p.target_roles) ? p.target_roles.join(', ') : '');
    setVal('prof-seniority-min', p.seniority_floor_years !== undefined ? p.seniority_floor_years : 0);
    setVal('prof-seniority-max', p.seniority_ceiling_years !== undefined ? p.seniority_ceiling_years : 3);
    setVal('prof-company-exclude', Array.isArray(p.company_exclude) ? p.company_exclude.join(', ') : '');
    setVal('prof-company-include', Array.isArray(p.company_include_only) ? p.company_include_only.join(', ') : '');

    // Safety & Pacing
    setVal('prof-stop-n', p.stop_after_n_applications || 5);
    setVal('prof-pace', p.pace_seconds_between_actions || 30);
    setVal('prof-freshness', p.job_freshness_days || 3);
    setVal('prof-browser-mode', p.browser_mode || 'visible');

  } catch (err) {
    showToast('Failed to load profile details: ' + err.message, 'error');
  }
}

function gatherProfileFromForm() {
  const parseList = (str) => (str || '').split(',').map(s => s.trim()).filter(Boolean);

  return {
    candidate_name: getVal('prof-name'),
    email: getVal('prof-email'),
    phone: getVal('prof-phone'),
    current_city: getVal('prof-city'),
    relocate_cities: parseList(getVal('prof-relocate')),

    target_roles: parseList(getVal('prof-target-roles')),

    total_experience_years: parseFloat(getVal('prof-exp')) || 0,
    notice_period_days: parseInt(getVal('prof-notice'), 10) || 0,
    current_ctc_lpa: parseFloat(getVal('prof-cur-ctc')) || 0,
    expected_ctc_lpa: parseFloat(getVal('prof-exp-ctc')) || 0,
    expected_ctc_text: getVal('prof-exp-text'),
    ctc_disclosure_policy: getVal('prof-policy'),

    immediately_available: getCheck('prof-immediate'),
    night_shift_ok: getCheck('prof-night'),
    weekend_ok: getCheck('prof-weekend'),

    highest_qualification: getVal('prof-highest-qual'),
    college: getVal('prof-college'),
    degree: getVal('prof-degree'),
    cgpa: getVal('prof-cgpa'),
    linkedin_url: getVal('prof-linkedin'),
    github_url: getVal('prof-github'),

    company_exclude: parseList(getVal('prof-company-exclude')),
    company_include_only: parseList(getVal('prof-company-include')),
    seniority_floor_years: parseInt(getVal('prof-seniority-min'), 10) || 0,
    seniority_ceiling_years: parseInt(getVal('prof-seniority-max'), 10) || 3,
    job_freshness_days: parseInt(getVal('prof-freshness'), 10) || 3,
    salary_floor_lpa: currentProfile.salary_floor_lpa || null,

    stop_after_n_applications: parseInt(getVal('prof-stop-n'), 10) || 5,
    pace_seconds_between_actions: parseInt(getVal('prof-pace'), 10) || 30,
    human_input_timeout_seconds: currentProfile.human_input_timeout_seconds || 120,
    max_pages_per_role: currentProfile.max_pages_per_role || 5,
    browser_mode: getVal('prof-browser-mode'),
    resume_file_name: currentProfile.resume_file_name || 'resume.pdf'
  };
}

async function saveActiveTabProfile() {
  const payload = gatherProfileFromForm();

  if (!payload.candidate_name) {
    showToast('Please enter your Candidate Name.', 'warning');
    switchTab('tab-profile');
    document.getElementById('prof-name').focus();
    return;
  }

  if (!payload.target_roles || payload.target_roles.length === 0) {
    showToast('Please specify at least one target role.', 'warning');
    switchTab('tab-preferences');
    document.getElementById('prof-target-roles').focus();
    return;
  }

  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast('Details saved permanently to profile.yaml!', 'success');
      currentProfile = payload;
      markSaved();
      refreshSystemStatus();
    } else {
      showToast('Error saving: ' + (data.error || 'Unknown error'), 'error');
    }
  } catch (err) {
    showToast('Save error: ' + err.message, 'error');
  }
}

/* ===================================================================
   Resume Upload
   =================================================================== */
function initDragAndDrop() {
  const dropZone = document.getElementById('drop-zone');

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('drag-over');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadResume(files[0]);
    }
  });
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (files && files.length > 0) {
    uploadResume(files[0]);
  }
}

async function uploadResume(file) {
  const validExts = ['.pdf', '.docx', '.doc'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

  if (!validExts.includes(ext)) {
    showToast('Please select a PDF or Word document (.pdf, .docx, .doc)', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('resume', file);

  const card = document.getElementById('upload-progress-card');
  const fill = document.getElementById('upload-progress-fill');
  const txt = document.getElementById('upload-progress-text');

  card.style.display = 'block';
  fill.style.width = '35%';
  txt.textContent = `Saving ${file.name}...`;

  try {
    fill.style.width = '75%';
    const res = await fetch('/api/upload-resume', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (data.success) {
      fill.style.width = '100%';
      txt.textContent = `Saved ${data.filename} to project!`;
      showToast(`Resume '${data.filename}' saved permanently to project files!`, 'success');

      currentProfile.resume_file_name = data.filename;

      setTimeout(() => {
        card.style.display = 'none';
        fill.style.width = '0%';
      }, 1200);

      refreshSystemStatus();
    } else {
      card.style.display = 'none';
      showToast(data.error || 'Failed to upload.', 'error');
    }
  } catch (err) {
    card.style.display = 'none';
    showToast('Upload failed: ' + err.message, 'error');
  }
}

/* ===================================================================
   API Keys & Secrets (.env)
   =================================================================== */
async function loadEnvKeys() {
  try {
    const res = await fetch('/api/env');
    const data = await res.json();
    if (data.gemini_api_key) setVal('env-gemini', data.gemini_api_key);
    if (data.groq_api_key) setVal('env-groq', data.groq_api_key);
    if (data.linkedin_username) setVal('env-linkedin-user', data.linkedin_username);
    if (data.naukri_username) setVal('env-naukri-user', data.naukri_username);

    if (data.has_linkedin_password) {
      const passEl = document.getElementById('env-linkedin-pass');
      if (passEl) passEl.placeholder = '•••••••• (Stored securely in .env)';
    }
    if (data.has_naukri_password) {
      const passEl = document.getElementById('env-naukri-pass');
      if (passEl) passEl.placeholder = '•••••••• (Stored securely in .env)';
    }
  } catch (err) {
    console.warn('Could not read keys:', err);
  }
}

async function saveEnvKeys() {
  const gemini = getVal('env-gemini');
  const groq = getVal('env-groq');
  const linkedinUser = getVal('env-linkedin-user');
  const linkedinPass = getVal('env-linkedin-pass');
  const naukriUser = getVal('env-naukri-user');
  const naukriPass = getVal('env-naukri-pass');

  if (!gemini) {
    showToast('Gemini API key is recommended to auto-draft screening answers.', 'warning');
  }

  const payload = {
    GEMINI_API_KEY: gemini,
    GROQ_API_KEY: groq,
    LINKEDIN_USERNAME: linkedinUser,
    LINKEDIN_PASSWORD: linkedinPass,
    NAUKRI_USERNAME: naukriUser,
    NAUKRI_PASSWORD: naukriPass,
  };

  try {
    const res = await fetch('/api/env', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast('Credentials & API keys saved permanently to .env file!', 'success');
      refreshSystemStatus();
    } else {
      showToast('Error saving: ' + (data.error || 'Unknown error'), 'error');
    }
  } catch (err) {
    showToast('Failed to save API keys: ' + err.message, 'error');
  }
}

async function connectPlatform(platform, mode) {
  if (isRunning) {
    showToast('An automation task is already running. Please stop it first.', 'warning');
    switchTab('tab-overview');
    return;
  }

  const siteName = platform === 'linkedin' ? 'LinkedIn' : 'Naukri';

  if (mode === 'auto') {
    const user = getVal(`env-${platform}-user`);
    const pass = getVal(`env-${platform}-pass`);

    if (!user) {
      showToast(`Please enter your ${siteName} username/email to use Auto-Login, or choose 'Manual Browser Login'.`, 'warning');
      switchTab('tab-credentials');
      document.getElementById(`env-${platform}-user`).focus();
      return;
    }

    // Save credentials to .env first
    const payload = {};
    payload[`${platform.toUpperCase()}_USERNAME`] = user;
    if (pass) {
      payload[`${platform.toUpperCase()}_PASSWORD`] = pass;
    }

    try {
      await fetch('/api/env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast(`Credentials saved! Launching ${siteName} Auto-Login...`, 'info');
    } catch (err) {
      showToast('Failed to save credentials: ' + err.message, 'error');
      return;
    }
  } else {
    showToast(`Opening visible browser window for manual ${siteName} login...`, 'info');
  }

  const action = platform === 'linkedin' ? 'login_linkedin' : 'login_naukri';
  startAutomation(action);
}

async function connectWithCookie(platform) {
  const input = document.getElementById(`cookie-${platform}-input`);
  const cookieText = (input ? input.value : '').trim();
  const siteName = platform === 'linkedin' ? 'LinkedIn' : 'Naukri';

  if (!cookieText) {
    showToast(`Please paste your ${siteName} cookie (e.g. ${platform === 'linkedin' ? 'li_at' : 'AUTHTOKEN'}) first.`, 'warning');
    if (input) input.focus();
    return;
  }

  showToast(`Connecting ${siteName} session via cookie...`, 'info');

  try {
    const res = await fetch('/api/session/cookie-connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, cookie_text: cookieText })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, 'success');
      if (input) input.value = '';
      await refreshSystemStatus();
    } else {
      showToast(data.error || 'Failed to connect cookie', 'error');
    }
  } catch (err) {
    showToast('Failed to connect cookie: ' + err.message, 'error');
  }
}

function togglePasswordVisibility(id) {
  const input = document.getElementById(id);
  if (input) {
    input.type = input.type === 'password' ? 'text' : 'password';
  }
}

/* ===================================================================
   Automation Control & Streaming Console
   =================================================================== */
async function startAutomation(action) {
  if (isRunning) {
    showToast('An automation task is already running. Stop it first.', 'warning');
    switchTab('tab-overview');
    return;
  }

  switchTab('tab-overview');
  appendLog(`Launching automation task: ${action}...`, 'system');

  try {
    const res = await fetch('/api/automation/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(data.message, 'info');
      refreshSystemStatus();
    } else if (data.warning) {
      showToast(data.warning, 'warning');
      appendLog(`⚠️ ${data.warning}`, 'warning');
    } else {
      showToast(data.error || 'Failed to start.', 'error');
      appendLog(`❌ ${data.error}`, 'error');
    }
  } catch (err) {
    showToast('Failed to start: ' + err.message, 'error');
    appendLog(`❌ Error: ${err.message}`, 'error');
  }
}

async function stopCurrentAutomation() {
  try {
    const res = await fetch('/api/automation/stop', { method: 'POST' });
    const data = await res.json();
    showToast(data.message || 'Automation stopped.', 'info');
    refreshSystemStatus();
  } catch (err) {
    showToast('Failed to stop: ' + err.message, 'error');
  }
}

function handleTermInputKey(e) {
  if (e.key === 'Enter') {
    sendTerminalInput();
  }
}

async function sendTerminalInput() {
  const input = document.getElementById('term-user-input');
  const text = input.value;
  input.value = '';

  try {
    await fetch('/api/automation/input', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
  } catch (err) {
    showToast('Failed to send input: ' + err.message, 'error');
  }
}

function initSSE() {
  if (sseSource) sseSource.close();
  sseSource = new EventSource('/api/automation/stream');

  sseSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload && payload.line !== undefined) {
        formatAndAppendLog(payload.line);
      }
    } catch (e) {
      // Keep-alive
    }
  };
}

function formatAndAppendLog(line) {
  let kind = 'normal';
  const lower = line.toLowerCase();

  if (lower.includes('[success]') || lower.includes('applied') || lower.includes('completed successfully')) {
    kind = 'success';
  } else if (lower.includes('error') || lower.includes('failed') || lower.includes('exception')) {
    kind = 'error';
  } else if (lower.includes('warning') || lower.includes('skip') || lower.includes('notice')) {
    kind = 'warning';
  } else if (lower.includes('user input') || lower.includes('prompt')) {
    kind = 'user';
  } else if (lower.startsWith('🚀') || lower.startsWith('🏁') || lower.startsWith('🛑')) {
    kind = 'info';
    refreshSystemStatus();
    loadApplicationLogs();
  }

  appendLog(line, kind);
}

function appendLog(text, kind = '') {
  const screen = document.getElementById('terminal-screen');
  const entry = document.createElement('div');
  entry.className = `log-entry ${kind}`;
  entry.textContent = text;
  screen.appendChild(entry);
  screen.scrollTop = screen.scrollHeight;
}

function clearConsoleLog() {
  document.getElementById('terminal-screen').innerHTML = '<div class="log-entry system">Console cleared.</div>';
}

function copyConsoleLog() {
  const screen = document.getElementById('terminal-screen');
  navigator.clipboard.writeText(screen.innerText).then(() => {
    showToast('Log copied to clipboard!', 'info');
  });
}

/* ===================================================================
   Application History Logs Table
   =================================================================== */
async function loadApplicationLogs() {
  try {
    const res = await fetch('/api/logs');
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.total || 0;
    document.getElementById('stat-applied').textContent = data.applied || 0;
    document.getElementById('stat-skipped').textContent = data.skipped || 0;
    document.getElementById('stat-stopped').textContent = data.stopped || 0;

    allLogs = data.rows || [];
    renderLogsTable();
  } catch (err) {
    console.warn('Failed to load logs:', err);
  }
}

function setStatusFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-pill').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-filter') === filter);
  });
  renderLogsTable();
}

function filterLogsTable() {
  renderLogsTable();
}

function renderLogsTable() {
  const tbody = document.getElementById('logs-table-body');
  const q = (document.getElementById('log-search-input').value || '').toLowerCase();

  const filtered = allLogs.filter(row => {
    const status = (row.status || '').toLowerCase();
    const matchF = currentFilter === 'all' || status.includes(currentFilter);
    const matchQ = !q ||
      (row.title || '').toLowerCase().includes(q) ||
      (row.company || '').toLowerCase().includes(q) ||
      (row.reason || '').toLowerCase().includes(q);
    return matchF && matchQ;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 30px; color: #94a3b8;">No application logs found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(row => {
    const s = (row.status || '').toLowerCase();
    let badgeClass = 'status-label';
    if (s.includes('applied')) badgeClass += ' applied';
    else if (s.includes('skip')) badgeClass += ' skipped';
    else badgeClass += ' stopped';

    return `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 0.76rem; color: #64748b;">${escapeHtml(row.timestamp || '—')}</td>
        <td style="font-weight: 600;">${escapeHtml(row.source || 'Naukri')}</td>
        <td style="font-weight: 600; color: #0f172a;">${escapeHtml(row.title || 'Untitled')}</td>
        <td style="color: #1e3a8a;">${escapeHtml(row.company || '—')}</td>
        <td><span class="${badgeClass}">${escapeHtml(row.status || 'unknown')}</span></td>
        <td style="font-size: 0.8rem; color: #475569; max-width: 320px;">${escapeHtml(row.reason || '—')}</td>
      </tr>
    `;
  }).join('');
}

/* ===================================================================
   Utilities & Helpers
   =================================================================== */
function initShortcuts() {
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveActiveTabProfile();
    }
  });
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconMap = {
    success: '✓',
    error: '✕',
    warning: '⚠️',
    info: 'ℹ'
  };

  toast.innerHTML = `<span>${iconMap[type] || '•'}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val !== undefined && val !== null ? val : '';
}

function getCheck(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function setCheck(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = Boolean(val);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
