import { api } from '../api/client.js';
import { formatDate } from '../utils/dates.js';
import { formatPercent } from '../utils/formatters.js';
import Handlebars from 'handlebars';
import emptyStateTemplate from '../templates/empty-state.hbs?raw';
import { initPerformanceChart } from '../charts/performance-chart.js';

const emptyTemplate = Handlebars.compile(emptyStateTemplate);

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold">Tableau de bord</h1>
        <div class="flex gap-3">
          <button id="update-prices" class="btn btn-primary" type="button">
            <i data-lucide="refresh-cw" class="w-5 h-5"></i>
            Mettre à jour les prix
          </button>
          <button id="refresh-dashboard" class="btn" type="button">
            <i data-lucide="refresh-cw" class="w-5 h-5"></i>
            Rafraîchir
          </button>
        </div>
      </div>
      <div id="dashboard-content" class="space-y-6"></div>
    </div>
  `;

  document.getElementById('refresh-dashboard')?.addEventListener('click', () => renderDashboard(container));
  document.getElementById('update-prices')?.addEventListener('click', async () => {
    const btn = document.getElementById('update-prices');
    btn.disabled = true;
    btn.innerHTML = 'Mise à jour…';
    try {
      const results = await api.post('/prices/update', { force_full: false });
      const successes = results.filter(r => r.status === 'success').length;
      const errors = results.filter(r => r.status === 'error').length;
      alert(`Mise à jour terminée : ${successes} succès, ${errors} erreurs.`);
    } catch (error) {
      alert(error.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="refresh-cw" class="w-5 h-5"></i> Mettre à jour les prix';
      renderDashboard(container);
    }
  });

  await loadDashboard(container);
}

async function loadDashboard(container) {
  const content = document.getElementById('dashboard-content');
  content.innerHTML = '<p class="text-text-muted text-sm">Chargement…</p>';
  try {
    // Récupérer les données de base
    const [dash, etfs] = await Promise.all([
      api.get('/dashboard'),
      api.get('/etfs')
    ]);

    // Récupérer les performances pour tous les ETF
    const performancePromises = etfs.map(async (etf) => {
      const perf = await api.get(`/etfs/${etf.id}/performance`);
      return { ...etf, ...perf };
    });
    const instrumentsWithPerf = await Promise.all(performancePromises);

    // Récupérer les signaux pour annotations et historique
    const signals = await api.get('/signals?limit=100');
    const latestSignal = signals.length > 0 ? signals[0] : null;
    const recentSignals = signals.slice(0, 5);

    // Filtrer les signaux pour les annotations (exclure HOLD_LEADER)
    const annotations = signals
      .filter(s => s.signal_type !== 'HOLD_LEADER')
      .map(s => ({
        date: s.signal_date,
        label: `${s.signal_type}${s.selected_instrument_id ? ' : ' + getEtfName(etfs, s.selected_instrument_id) : ''}`,
        signal_type: s.signal_type
      }));

    // Récupérer le commentaire IA (peut ne pas exister)
    let aiCommentary = null;
    try {
      aiCommentary = await api.get('/ai/commentary/latest');
    } catch (_) {
      // pas de commentaire
    }

    // Construire le contenu HTML
    content.innerHTML = `
      <!-- KPI en haut -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card">
          <p class="text-sm text-text-muted">Dernière actualisation</p>
          <p class="text-xl font-semibold mt-1">${formatDate(dash.last_update)}</p>
        </div>
        <div class="card">
          <p class="text-sm text-text-muted">ETF suivis</p>
          <p class="text-xl font-semibold mt-1">${dash.counts.active_etfs}</p>
        </div>
        <div class="card">
          <p class="text-sm text-text-muted">Benchmarks</p>
          <p class="text-xl font-semibold mt-1">${dash.counts.benchmarks}</p>
        </div>
        <div class="card">
          <p class="text-sm text-text-muted">Signal actuel</p>
          <p class="text-xl font-semibold mt-1">${dash.signal.message}</p>
        </div>
      </section>

      <!-- Prochain contrôle et dernier signal détaillé -->
      <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="card">
          <h2 class="text-lg font-medium mb-3">Prochain contrôle mensuel</h2>
          <p>${formatDate(dash.next_control_date)}</p>
        </div>
        <div class="card">
          <h2 class="text-lg font-medium mb-3">Dernier signal</h2>
          ${latestSignal ? `
            <div class="space-y-2">
              <p class="flex items-center gap-2">
                <span class="badge ${signalBadgeClass(latestSignal.signal_type)}">${latestSignal.signal_type}</span>
              </p>
              <p class="text-sm text-text-muted">Date : ${formatDate(latestSignal.signal_date)}</p>
              ${latestSignal.selected_instrument_id ? `<p class="text-sm text-text-muted">Instrument : ${getEtfName(etfs, latestSignal.selected_instrument_id)}</p>` : ''}
              ${latestSignal.leader_score !== null ? `<p class="text-sm text-text-muted">Score leader : ${formatPercent(latestSignal.leader_score)}</p>` : ''}
              ${latestSignal.score_gap !== null ? `<p class="text-sm text-text-muted">Écart : ${formatPercent(latestSignal.score_gap)}</p>` : ''}
            </div>
          ` : '<p class="text-sm text-text-muted">Aucun signal calculé.</p>'}
        </div>
      </section>

      <!-- Graphique principal -->
      <section class="card">
        <h2 class="text-lg font-medium mb-3">Performance relative</h2>
        <div id="performance-chart-container"></div>
      </section>

      <!-- Historique récent des signaux -->
      <section class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-medium">Signaux récents</h2>
          <a href="#/signals" class="btn btn-sm">Voir tout</a>
        </div>
        ${renderRecentSignals(recentSignals, etfs)}
      </section>

      <!-- Commentaire IA -->
      <section class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-medium">Commentaire IA</h2>
          <button id="generate-ai" class="btn btn-sm btn-primary">Générer</button>
        </div>
        <div id="ai-commentary">
          ${aiCommentary ? `
            <div class="space-y-2">
              <p class="font-medium">${aiCommentary.summary}</p>
              <p class="text-sm">${aiCommentary.decision_explained}</p>
              ${aiCommentary.risk_note ? `<p class="text-sm text-text-muted">${aiCommentary.risk_note}</p>` : ''}
              <p class="text-xs text-text-muted">Provider : ${aiCommentary.provider}${aiCommentary.model_name ? ' - ' + aiCommentary.model_name : ''}</p>
            </div>
          ` : '<p class="text-sm text-text-muted">Aucun commentaire IA généré.</p>'}
        </div>
      </section>

      <!-- Tableau des performances -->
      <section class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-medium">Performances des instruments</h2>
        </div>
        ${renderPerformanceTable(instrumentsWithPerf)}
      </section>
    `;

    // Initialiser le graphique avec les instruments actifs et les annotations
    const activeEtfs = etfs.filter(e => e.is_active);
    const chartContainer = document.getElementById('performance-chart-container');
    if (chartContainer && activeEtfs.length > 0) {
      initPerformanceChart(chartContainer, activeEtfs, annotations);
    } else if (chartContainer) {
      chartContainer.innerHTML = '<p class="text-sm text-text-muted">Aucun instrument actif pour le graphique.</p>';
    }

    // Gestion du bouton "Générer" pour l'IA
    document.getElementById('generate-ai')?.addEventListener('click', async () => {
      const btn = document.getElementById('generate-ai');
      btn.disabled = true;
      btn.innerHTML = 'Génération…';
      try {
        const result = await api.post('/ai/commentary', { force: true });
        // Mettre à jour l'affichage
        const aiDiv = document.getElementById('ai-commentary');
        aiDiv.innerHTML = `
          <div class="space-y-2">
            <p class="font-medium">${result.summary}</p>
            <p class="text-sm">${result.decision_explained}</p>
            ${result.risk_note ? `<p class="text-sm text-text-muted">${result.risk_note}</p>` : ''}
            <p class="text-xs text-text-muted">Provider : ${result.provider}${result.model_name ? ' - ' + result.model_name : ''}</p>
          </div>
        `;
      } catch (error) {
        alert(error.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = 'Générer';
      }
    });

  } catch (error) {
    content.innerHTML = `
      <div class="card border-negative/30 bg-negative/10 text-negative p-4 flex items-start gap-3" role="alert">
        <i data-lucide="alert-triangle" class="w-5 h-5 mt-0.5"></i>
        <div>
          <p class="font-medium">Impossible de charger le tableau de bord</p>
          <p class="text-sm">${error.message}</p>
        </div>
      </div>
    `;
  }
}

/**
 * Retourne le nom d'un ETF à partir de son ID.
 */
function getEtfName(etfs, instrumentId) {
  const inst = etfs.find(e => e.id === Number(instrumentId));
  return inst ? inst.name : 'Instrument inconnu';
}

/**
 * Retourne la classe CSS de badge selon le type de signal.
 */
function signalBadgeClass(signalType) {
  switch (signalType) {
    case 'CASH':
      return 'badge-negative';
    case 'ROTATE_TO_LEADER':
      return 'badge-teal';
    case 'HOLD_LEADER':
      return 'badge-positive';
    default:
      return 'badge-muted';
  }
}

/**
 * Affiche une mini-table des derniers signaux.
 */
function renderRecentSignals(signals, etfs) {
  if (!signals.length) {
    return emptyTemplate({ message: 'Aucun signal enregistré.' });
  }
  return `
    <div class="overflow-x-auto">
      <table class="table-base min-w-[600px]">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Instrument</th>
            <th>Score</th>
            <th>Écart</th>
          </tr>
        </thead>
        <tbody>
          ${signals.map(sig => `
            <tr>
              <td class="py-2 pr-4">${formatDate(sig.signal_date)}</td>
              <td class="py-2 pr-4"><span class="badge ${signalBadgeClass(sig.signal_type)}">${sig.signal_type}</span></td>
              <td class="py-2 pr-4">${sig.selected_instrument_id ? getEtfName(etfs, sig.selected_instrument_id) : '—'}</td>
              <td class="py-2 pr-4">${sig.leader_score !== null ? formatPercent(sig.leader_score) : '—'}</td>
              <td class="py-2 pr-4">${sig.score_gap !== null ? formatPercent(sig.score_gap) : '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Affiche le tableau complet des performances.
 */
function renderPerformanceTable(instruments) {
  const active = instruments.filter(i => i.is_active);
  if (!active.length) {
    return emptyTemplate({ message: 'Aucun instrument actif.' });
  }

  return `
    <div class="overflow-x-auto">
      <table class="table-base min-w-[900px]">
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Dernier close</th>
            <th>SMA200</th>
            <th>Statut SMA</th>
            <th>1M</th>
            <th>3M</th>
            <th>6M</th>
            <th>12M</th>
          </tr>
        </thead>
        <tbody>
          ${active.map(inst => `
            <tr>
              <td class="py-3 pr-4 font-medium">
                ${inst.name}
                ${inst.is_benchmark ? '<span class="badge badge-teal ml-1">Benchmark</span>' : ''}
              </td>
              <td class="py-3 pr-4">${inst.last_close ? inst.last_close.toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—'}</td>
              <td class="py-3 pr-4">${inst.sma200 ? inst.sma200.toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—'}</td>
              <td class="py-3 pr-4">
                ${inst.above_sma200 === null ? '—' : inst.above_sma200 ? '<span class="badge badge-positive">Au-dessus</span>' : '<span class="badge badge-negative">Sous</span>'}
              </td>
              <td class="py-3 pr-4">${formatPercent(inst.perf_1m)}</td>
              <td class="py-3 pr-4">${formatPercent(inst.perf_3m)}</td>
              <td class="py-3 pr-4">${formatPercent(inst.perf_6m)}</td>
              <td class="py-3 pr-4">${formatPercent(inst.perf_12m)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}