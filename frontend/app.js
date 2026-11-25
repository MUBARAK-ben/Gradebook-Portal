
const API_BASE = "https://gradebook-portal.onrender.com";
const classFilterEl = document.getElementById("class-filter");
const apiStatusEl = document.getElementById("api-status");
const toastEl = document.getElementById("toast");

const attDateEl = document.getElementById("att-date");
attDateEl.value = new Date().toISOString().split("T")[0];

function showToast(message, type = "success") {
  toastEl.textContent = message;
  toastEl.className = `toast ${type}`;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toastEl.className = "toast hidden";
  }, 3500);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    let detail = "Request failed.";
    try {
      const errData = await response.json();
      detail = errData.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

async function checkHealth() {
  try {
    await apiFetch("/api/health");
    apiStatusEl.textContent = "API Online";
    apiStatusEl.className = "badge badge-online";
  } catch {
    apiStatusEl.textContent = "API Offline";
    apiStatusEl.className = "badge badge-offline";
  }
}

async function loadClasses() {
  const current = classFilterEl.value;
  const classes = await apiFetch("/api/classes");
  classFilterEl.innerHTML = `<option value="">All Classes</option>`;
  classes.forEach((cls) => {
    const opt = document.createElement("option");
    opt.value = cls;
    opt.textContent = cls;
    classFilterEl.appendChild(opt);
  });
  if (classes.includes(current)) {
    classFilterEl.value = current;
  }
}

async function loadStudentDropdowns() {
  const selectedClass = classFilterEl.value;
  const query = selectedClass ? `?class_name=${encodeURIComponent(selectedClass)}` : "";
  const students = await apiFetch(`/api/students${query}`);

  const targets = [document.getElementById("att-reg"), document.getElementById("score-reg")];
  targets.forEach((select) => {
    select.innerHTML = `<option value="">Select student...</option>`;
    students.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.reg_no;
      opt.textContent = `${s.full_name} (${s.reg_no} - ${s.class_name})`;
      select.appendChild(opt);
    });
  });
}

async function loadSummary() {
  const selectedClass = classFilterEl.value;
  const query = selectedClass ? `?class_name=${encodeURIComponent(selectedClass)}` : "";
  const rows = await apiFetch(`/api/summary${query}`);

  document.getElementById("summary-count").textContent = `${rows.length} student(s)`;
  const tbody = document.getElementById("summary-body");

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="9" class="muted center">No students found for this selection.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows
    .map(
      (r, index) => `
      <tr>
        <td>${index + 1}</td>
        <td><strong>${r.reg_no}</strong></td>
        <td>${r.full_name}</td>
        <td>${r.class_name}</td>
        <td>${r.assessments}</td>
        <td>${r.avg_percentage}%</td>
        <td><span class="grade-pill">${r.grade}</span></td>
        <td>${r.attendance_pct}% (${r.sessions})</td>
        <td>
          <button class="btn btn-danger" onclick="removeStudent(${r.id}, '${r.full_name.replace(/'/g, "\\'")}')">
            Delete
          </button>
        </td>
      </tr>
    `
    )
    .join("");
}

async function loadScores() {
  const selectedClass = classFilterEl.value;
  const query = selectedClass ? `?class_name=${encodeURIComponent(selectedClass)}` : "";
  const scores = await apiFetch(`/api/scores${query}`);

  document.getElementById("scores-count").textContent = `${scores.length} entry(s)`;
  const tbody = document.getElementById("scores-body");

  if (!scores.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted center">No scores recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = scores
    .map((sc) => {
      const pct = ((sc.score / sc.max_score) * 100).toFixed(1);
      return `
        <tr>
          <td>${sc.full_name}</td>
          <td>${sc.reg_no}</td>
          <td>${sc.class_name}</td>
          <td>${sc.assessment_title}</td>
          <td>${sc.score} / ${sc.max_score}</td>
          <td>${pct}%</td>
          <td>
            <button class="btn btn-danger" onclick="removeScore(${sc.id})">Remove</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function refreshAll() {
  try {
    await checkHealth();
    await loadClasses();
    await Promise.all([loadStudentDropdowns(), loadSummary(), loadScores()]);
  } catch (err) {
  showToast(err.message || "Could not reach the backend server.", "error");
}
}

document.getElementById("student-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      full_name: document.getElementById("student-name").value,
      reg_no: document.getElementById("student-reg").value,
      class_name: document.getElementById("student-class").value,
    };
    const created = await apiFetch("/api/students", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    e.target.reset();
    showToast(`Added ${created.full_name} (${created.reg_no}).`);
    await refreshAll();
  } catch (err) {
    showToast(err.message, "error");
  }
});

document.getElementById("attendance-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      reg_no: document.getElementById("att-reg").value,
      status: document.getElementById("att-status").value,
      session_date: document.getElementById("att-date").value,
    };
    const res = await apiFetch("/api/attendance", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(`Marked ${res.full_name} as ${res.status} on ${res.session_date}.`);
    await loadSummary();
  } catch (err) {
    showToast(err.message, "error");
  }
});

document.getElementById("score-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      reg_no: document.getElementById("score-reg").value,
      assessment_title: document.getElementById("score-title").value,
      score: parseFloat(document.getElementById("score-val").value),
      max_score: parseFloat(document.getElementById("score-max").value),
    };
    const res = await apiFetch("/api/scores", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    document.getElementById("score-title").value = "";
    document.getElementById("score-val").value = "";
    showToast(`Recorded ${res.score}/${res.max_score} for ${res.full_name}.`);
    await Promise.all([loadSummary(), loadScores()]);
  } catch (err) {
    showToast(err.message, "error");
  }
});

window.removeStudent = async function (studentId, name) {
  if (!confirm(`Delete ${name} and all their attendance and score records?`)) return;
  try {
    await apiFetch(`/api/students/${studentId}`, { method: "DELETE" });
    showToast(`Deleted ${name}.`);
    await refreshAll();
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.removeScore = async function (scoreId) {
  try {
    await apiFetch(`/api/scores/${scoreId}`, { method: "DELETE" });
    showToast("Score entry removed.");
    await Promise.all([loadSummary(), loadScores()]);
  } catch (err) {
    showToast(err.message, "error");
  }
};

classFilterEl.addEventListener("change", () => {
  Promise.all([loadStudentDropdowns(), loadSummary(), loadScores()]);
});

document.getElementById("export-btn").addEventListener("click", () => {
  const selectedClass = classFilterEl.value;
  const query = selectedClass ? `?class_name=${encodeURIComponent(selectedClass)}` : "";
  window.open(`${API_BASE}/api/export.csv${query}`, "_blank");
});

refreshAll();