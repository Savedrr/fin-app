/* FinanceApp — main.js — Shared utilities, state, and sidebar */

// ── Month State ──────────────────────────────────────────────────────────────
window.AppState = {
  month: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
};

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

function updateMonthLabel() {
  const el = document.getElementById('monthLabel');
  if (el) el.textContent = MONTHS[AppState.month - 1] + '/' + String(AppState.year).slice(2);
}

document.addEventListener('DOMContentLoaded', () => {
  updateMonthLabel();

  const prev = document.getElementById('prevMonth');
  const next = document.getElementById('nextMonth');

  if (prev) prev.addEventListener('click', () => {
    AppState.month--;
    if (AppState.month < 1) { AppState.month = 12; AppState.year--; }
    updateMonthLabel();
    if (typeof onMonthChange === 'function') onMonthChange();
  });

  if (next) next.addEventListener('click', () => {
    AppState.month++;
    if (AppState.month > 12) { AppState.month = 1; AppState.year++; }
    updateMonthLabel();
    if (typeof onMonthChange === 'function') onMonthChange();
  });
});

// ── Sidebar Toggle ───────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('open');
}

// ── Formatting ───────────────────────────────────────────────────────────────
function fmtBRL(n) {
  return 'R$ ' + Number(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function fmtShortDate(iso) {
  if (!iso) return '';
  const [, m, d] = iso.split('-');
  return `${d}/${MONTHS[parseInt(m)-1]}`;
}

// ── API Helpers ───────────────────────────────────────────────────────────────
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  if (!res.ok && res.status === 401) {
    window.location.href = '/login';
    return null;
  }
  return res.json();
}

async function apiGet(path) { return api(path); }
async function apiPost(path, body) { return api(path, { method: 'POST', body }); }
async function apiPut(path, body) { return api(path, { method: 'PUT', body }); }
async function apiDelete(path) { return api(path, { method: 'DELETE' }); }

// ── Toast Notifications ───────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const t = document.createElement('div');
  t.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    padding:12px 20px;border-radius:12px;font-size:13px;font-weight:500;
    animation:slideIn .25s ease;max-width:320px;line-height:1.5;
    background:${type==='success'?'#0D6E44':type==='error'?'#B91C1C':'#1D4ED8'};
    color:#fff;box-shadow:0 8px 32px rgba(0,0,0,0.4);
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

// ── Modal Helpers ────────────────────────────────────────────────────────────
function showModal(html) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `<div class="modal">${html}</div>`;
  backdrop.addEventListener('click', e => { if (e.target === backdrop) backdrop.remove(); });
  document.body.appendChild(backdrop);
  return backdrop;
}

function closeModal() {
  document.querySelector('.modal-backdrop')?.remove();
}

// ── Chart Defaults ────────────────────────────────────────────────────────────
Chart.defaults.color = '#6B7394';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'DM Sans', sans-serif";
