import { api } from '../api/client.js';
import Handlebars from 'handlebars';
import etfRowTemplate from '../templates/etf-row.hbs?raw';
import emptyStateTemplate from '../templates/empty-state.hbs?raw';

const rowTemplate = Handlebars.compile(etfRowTemplate);
const emptyTemplate = Handlebars.compile(emptyStateTemplate);

let instrumentsCache = [];

export async function renderEtfs(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold">ETF & Benchmarks</h1>
        <button id="show-form" class="btn btn-primary" type="button">
          <i data-lucide="plus" class="w-5 h-5"></i>
          Ajouter un instrument
        </button>
      </div>

      <div id="form-container" class="hidden"></div>
      <div id="csv-container" class="hidden"></div>
      <div id="list-container"></div>
    </div>
  `;

  document.getElementById('show-form')?.addEventListener('click', () => showForm(container));
  document.getElementById('list-container')?.addEventListener('click', handleListClick);

  await loadList(container);
}

async function loadList(container) {
  const listContainer = document.getElementById('list-container');
  listContainer.innerHTML = '<p class="text-text-muted text-sm">Chargement…</p>';
  try {
    instrumentsCache = await api.get('/etfs');
    renderList();
  } catch (error) {
    listContainer.innerHTML = errorBox(error.message);
  }
}

function renderList() {
  const listContainer = document.getElementById('list-container');
  if (!instrumentsCache.length) {
    listContainer.innerHTML = `<div class="card">${emptyTemplate({ message: 'Aucun instrument. Ajoutez votre premier ETF ou benchmark.' })}</div>`;
    return;
  }
  listContainer.innerHTML = `
    <div class="card overflow-x-auto">
      <table class="table-base min-w-[700px]">
        <thead>
          <tr>
            <th>Nom</th>
            <th>ISIN</th>
            <th>Yahoo</th>
            <th>Devise</th>
            <th>Rôle</th>
            <th>Statut</th>
            <th class="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${instrumentsCache.map(etf => rowTemplate(etf)).join('')}
        </tbody>
      </table>
    </div>
  `;
}

async function handleListClick(event) {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const { action, id } = button.dataset;

  if (action === 'edit') {
    const instrument = instrumentsCache.find(i => i.id === Number(id));
    if (instrument) showForm(document.getElementById('view-container'), instrument);
  }

  if (action === 'delete') {
    const instrument = instrumentsCache.find(i => i.id === Number(id));
    if (!instrument) return;
    const confirmDelete = window.confirm(`Supprimer définitivement ${instrument.name} ?`);
    if (!confirmDelete) return;
    try {
      await api.delete(`/etfs/${id}`);
      await loadList(document.getElementById('view-container'));
    } catch (error) {
      alert(error.message);
    }
  }

  if (action === 'test') {
    const instrument = instrumentsCache.find(i => i.id === Number(id));
    if (!instrument) return;
    try {
      const result = await api.post(`/etfs/${id}/test-ticker`);
      if (result.status === 'ok') {
        alert(`Ticker OK : ${result.message}`);
      } else {
        alert(`Erreur ticker : ${result.message}`);
      }
    } catch (error) {
      alert(error.message);
    }
  }
}

function showForm(container, instrument = null) {
  const formContainer = document.getElementById('form-container');
  const isEdit = Boolean(instrument);

  formContainer.innerHTML = `
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-medium">${isEdit ? 'Modifier' : 'Ajouter'} un instrument</h2>
        <button id="close-form" class="btn btn-sm" type="button" aria-label="Fermer">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <form id="etf-form" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${!isEdit ? `
        <div class="md:col-span-2">
          <label class="label" for="lookup-query">Rechercher par ISIN ou ticker Yahoo</label>
          <div class="flex gap-2">
            <input id="lookup-query" class="input" placeholder="Ex: FR0010750172 ou CW8.PA" />
            <button id="lookup-btn" type="button" class="btn btn-primary">Rechercher</button>
          </div>
          <p class="text-xs text-text-muted mt-1">Les champs ci-dessous seront remplis automatiquement.</p>
        </div>
        ` : ''}
        <div>
          <label class="label" for="isin">ISIN</label>
          <input id="isin" class="input" required maxlength="12" placeholder="FR0012345678" value="${instrument?.isin || ''}" />
        </div>
        <div>
          <label class="label" for="yahoo_symbol">Ticker Yahoo Finance</label>
          <input id="yahoo_symbol" class="input" required placeholder="CW8.PA, SPY, ..." value="${instrument?.yahoo_symbol || ''}" />
          <p class="text-xs text-text-muted mt-1">Exemples de suffixes : .PA (Paris), .L (Londres), .DE (Francfort), .AS (Amsterdam).</p>
        </div>
        <div>
          <label class="label" for="name">Nom</label>
          <input id="name" class="input" required value="${instrument?.name || ''}" />
        </div>
        <div>
          <label class="label" for="currency">Devise</label>
          <input id="currency" class="input" required maxlength="3" value="${instrument?.currency || 'EUR'}" />
        </div>
        <div>
          <label class="label" for="exchange">Place de cotation</label>
          <input id="exchange" class="input" value="${instrument?.exchange || ''}" />
        </div>
        <div>
          <label class="label" for="region">Région</label>
          <input id="region" class="input" value="${instrument?.region || ''}" />
        </div>
        <div class="flex items-center gap-3 md:col-span-2">
          <label class="flex items-center gap-2">
            <input id="is_active" type="checkbox" ${instrument?.is_active !== false ? 'checked' : ''} class="rounded border-border" />
            <span class="text-sm">Actif</span>
          </label>
          <label class="flex items-center gap-2">
            <input id="is_benchmark" type="checkbox" ${instrument?.is_benchmark ? 'checked' : ''} class="rounded border-border" />
            <span class="text-sm">Benchmark</span>
          </label>
        </div>
        <div class="md:col-span-2 flex gap-3">
          <button type="submit" class="btn btn-primary">${isEdit ? 'Enregistrer' : 'Créer'}</button>
          <button id="show-csv-import" class="btn" type="button">Importer des prix CSV</button>
        </div>
      </form>
    </div>
  `;

  formContainer.classList.remove('hidden');

  document.getElementById('close-form')?.addEventListener('click', () => {
    formContainer.classList.add('hidden');
    formContainer.innerHTML = '';
  });

  // Gestion de la recherche automatique
  const lookupBtn = document.getElementById('lookup-btn');
  if (lookupBtn) {
    lookupBtn.addEventListener('click', async () => {
      const query = document.getElementById('lookup-query').value.trim();
      if (!query) {
        alert('Veuillez saisir un ISIN ou un ticker.');
        return;
      }
      lookupBtn.disabled = true;
      lookupBtn.innerHTML = 'Recherche…';
      try {
        const result = await api.post('/etfs/lookup', { query });
        document.getElementById('isin').value = result.isin || '';
        document.getElementById('yahoo_symbol').value = result.yahoo_symbol || '';
        document.getElementById('name').value = result.name || '';
        document.getElementById('currency').value = result.currency || 'EUR';
        document.getElementById('exchange').value = result.exchange || '';
        document.getElementById('region').value = result.region || '';
        alert('Métadonnées récupérées. Vérifiez et complétez si nécessaire.');
      } catch (error) {
        alert(`Erreur de recherche : ${error.message}`);
      } finally {
        lookupBtn.disabled = false;
        lookupBtn.innerHTML = 'Rechercher';
      }
    });
  }

  // Gestion de la soumission du formulaire
  document.getElementById('etf-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      isin: document.getElementById('isin').value,
      yahoo_symbol: document.getElementById('yahoo_symbol').value,
      name: document.getElementById('name').value,
      currency: document.getElementById('currency').value.toUpperCase(),
      exchange: document.getElementById('exchange').value || null,
      region: document.getElementById('region').value || null,
      is_active: document.getElementById('is_active').checked,
      is_benchmark: document.getElementById('is_benchmark').checked
    };

    try {
      if (isEdit) {
        await api.patch(`/etfs/${instrument.id}`, payload);
      } else {
        await api.post('/etfs', payload);
      }
      formContainer.classList.add('hidden');
      formContainer.innerHTML = '';
      await loadList(container);
    } catch (error) {
      alert(error.message);
    }
  });

  // Gestion de l'import CSV
  document.getElementById('show-csv-import')?.addEventListener('click', () => {
    showCsvImport(container);
  });
}

function showCsvImport(container) {
  const csvContainer = document.getElementById('csv-container');
  csvContainer.innerHTML = `
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-medium">Import CSV manuel</h2>
        <button id="close-csv" class="btn btn-sm" type="button" aria-label="Fermer">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="space-y-4">
        <div>
          <label class="label" for="csv-instrument">Instrument cible</label>
          <select id="csv-instrument" class="input">
            ${instrumentsCache.map(i => `<option value="${i.id}">${i.name} (${i.yahoo_symbol})</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="label" for="csv-file">Fichier CSV</label>
          <input id="csv-file" type="file" accept=".csv" class="input" />
          <p class="text-xs text-text-muted mt-1">Colonnes minimales : <code>Date</code>, <code>Close</code>. Optionnel : <code>Open</code>, <code>High</code>, <code>Low</code>, <code>Volume</code>.</p>
        </div>
        <div id="csv-preview"></div>
        <button id="csv-import-btn" class="btn btn-primary" disabled>
          <i data-lucide="upload" class="w-5 h-5"></i>
          Importer
        </button>
      </div>
    </div>
  `;

  csvContainer.classList.remove('hidden');
  document.getElementById('close-csv')?.addEventListener('click', () => {
    csvContainer.classList.add('hidden');
    csvContainer.innerHTML = '';
  });

  const fileInput = document.getElementById('csv-file');
  const previewDiv = document.getElementById('csv-preview');
  const importBtn = document.getElementById('csv-import-btn');

  fileInput?.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) {
      previewDiv.innerHTML = '';
      importBtn.disabled = true;
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) {
        previewDiv.innerHTML = '<p class="text-sm text-negative">Le fichier doit contenir au moins un en-tête et une ligne.</p>';
        importBtn.disabled = true;
        return;
      }
      const header = lines[0].split(',');
      const firstRows = lines.slice(1, 6).map(line => line.split(','));
      let previewHtml = `<p class="text-sm text-text-muted mb-2">Aperçu des 5 premières lignes :</p>
        <div class="overflow-x-auto"><table class="table-base">
          <thead><tr>${header.map(h => `<th>${h.trim()}</th>`).join('')}</tr></thead>
          <tbody>${firstRows.map(row => `<tr>${row.map(cell => `<td>${cell.trim()}</td>`).join('')}</tr>`).join('')}</tbody>
        </table></div>`;
      previewDiv.innerHTML = previewHtml;
      importBtn.disabled = false;
    };
    reader.readAsText(file);
  });

  importBtn?.addEventListener('click', async () => {
    const file = fileInput.files[0];
    const instrumentId = document.getElementById('csv-instrument').value;
    if (!file || !instrumentId) return;

    const formData = new FormData();
    formData.append('instrument_id', instrumentId);
    formData.append('file', file);

    importBtn.disabled = true;
    importBtn.textContent = 'Import en cours…';
    try {
      const response = await api.upload('/prices/import-csv', formData);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Erreur import');
      alert(`Import réussi : ${result.total} lignes (${result.inserted} ajoutées, ${result.updated} mises à jour).`);
      csvContainer.classList.add('hidden');
      csvContainer.innerHTML = '';
    } catch (error) {
      alert(error.message);
      importBtn.disabled = false;
      importBtn.innerHTML = '<i data-lucide="upload" class="w-5 h-5"></i> Importer';
    }
  });
}

function errorBox(message) {
  return `
    <div class="card border-negative/30 bg-negative/10 text-negative p-4 flex items-start gap-3" role="alert">
      <i data-lucide="alert-triangle" class="w-5 h-5 mt-0.5"></i>
      <p>${message}</p>
    </div>
  `;
}