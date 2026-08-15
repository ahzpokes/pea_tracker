import { api } from '../api/client.js';
import { formatDate, formatDateTime } from '../utils/dates.js';
import { formatPercent } from '../utils/formatters.js';
import Handlebars from 'handlebars';
import signalHistoryTemplate from '../templates/signal-history-row.hbs?raw';

const template = Handlebars.compile(signalHistoryTemplate);

export async function renderSignals(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold">Historique des signaux</h1>
        <button id="calculate-signal" class="btn btn-primary">
          <i data-lucide="calculator" class="w-5 h-5"></i>
          Calculer le signal
        </button>
      </div>
      <div id="signals-content"></div>
    </div>
  `;

  document.getElementById('calculate-signal')?.addEventListener('click', async () => {
    const btn = document.getElementById('calculate-signal');
    btn.disabled = true;
    btn.innerHTML = 'Calcul…';
    try {
      await api.post('/signals/calculate');
      await loadSignals(container);
    } catch (error) {
      alert(error.message);
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="calculator" class="w-5 h-5"></i> Calculer le signal';
    }
  });

  await loadSignals(container);
}

async function loadSignals(container) {
  const content = document.getElementById('signals-content');
  content.innerHTML = '<p class="text-text-muted text-sm">Chargement…</p>';
  try {
    const signals = await api.get('/signals?limit=100');
    // Récupérer les noms des instruments pour le template
    const etfs = await api.get('/etfs');
    const etfMap = Object.fromEntries(etfs.map(e => [e.id, e.name]));

    if (!signals.length) {
      content.innerHTML = `
        <div class="card">
          <p class="text-sm text-text-muted">Aucun signal calculé pour le moment.</p>
        </div>
      `;
      return;
    }

    const rows = signals.map(sig => {
      return {
        ...sig,
        signal_date: formatDate(sig.signal_date),
        selected_instrument_name: sig.selected_instrument_id ? etfMap[sig.selected_instrument_id] : null,
        leader_score_pct: sig.leader_score !== null ? formatPercent(sig.leader_score) : '—',
        score_gap_pct: sig.score_gap !== null ? formatPercent(sig.score_gap) : '—',
        leader_sma200: sig.leader_sma200 ? sig.leader_sma200.toFixed(2) : '—',
        threshold_used_pct: sig.threshold_used !== null ? formatPercent(sig.threshold_used) : '—'
      };
    });

    content.innerHTML = `
      <div class="card overflow-x-auto">
        <table class="table-base min-w-[900px]">
          <thead>
            <tr>
              <th>Date</th>
              <th>Instrument sélectionné</th>
              <th>Type</th>
              <th>Score leader</th>
              <th>Écart</th>
              <th>SMA200 leader</th>
              <th>Seuil</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => template(row)).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (error) {
    content.innerHTML = `
      <div class="card border-negative/30 bg-negative/10 text-negative p-4">${error.message}</div>
    `;
  }
}