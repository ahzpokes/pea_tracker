import ApexCharts from 'apexcharts';
import { api } from '../api/client.js';
import { formatPercent } from '../utils/formatters.js';

export function initPerformanceChart(container, instruments, annotations = []) {
  container.innerHTML = `
    <div class="space-y-4">
      <div class="flex flex-wrap gap-3 items-center justify-between">
        <div class="flex items-center gap-2">
          <label for="period-select" class="text-sm text-text-muted">Période :</label>
          <select id="period-select" class="input w-auto">
            <option value="1M">1M</option>
            <option value="3M">3M</option>
            <option value="6M">6M</option>
            <option value="12M" selected>12M</option>
            <option value="Max">Max</option>
          </select>
        </div>
        <div id="series-filters" class="flex flex-wrap gap-3">
          ${instruments.map(inst => `
            <label class="flex items-center gap-1.5 text-sm">
              <input type="checkbox" class="series-checkbox rounded" value="${inst.id}" checked>
              <span>${inst.name}</span>
            </label>
          `).join('')}
        </div>
      </div>
      <div id="chart"></div>
      <div id="perf-table"></div>
    </div>
  `;

  const periodSelect = document.getElementById('period-select');
  const chartEl = document.getElementById('chart');
  const perfTableEl = document.getElementById('perf-table');
  let chart = null;

  const isDark = document.documentElement.classList.contains('dark');
  const textColor = getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim();
  const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border').trim();

  function getSelectedIds() {
    return Array.from(document.querySelectorAll('.series-checkbox:checked')).map(cb => cb.value);
  }

  async function loadData() {
    const period = periodSelect.value;
    const ids = getSelectedIds();
    if (!ids.length) {
      chartEl.innerHTML = '<p class="text-text-muted text-sm">Sélectionnez au moins un instrument.</p>';
      perfTableEl.innerHTML = '';
      return;
    }
    try {
      const data = await api.get(`/charts/performance?period=${period}&instrument_ids=${ids.join(',')}`);
      renderChart(data);
      renderTable(data);
    } catch (error) {
      chartEl.innerHTML = `<div class="text-negative">${error.message}</div>`;
      perfTableEl.innerHTML = '';
    }
  }

  function renderChart(data) {
    const colors = ['#008080', '#011D25', '#4DDEDD', '#00AAAA', '#F5BD68', '#F58B8B', '#5FD49C', '#A8C7C8'];
    const series = data.series.map((s, idx) => {
      const color = s.is_benchmark ? '#557078' : colors[idx % colors.length];
      const dashArray = s.is_benchmark ? 5 : 0;
      return {
        name: s.name,
        type: 'line',
        data: s.values.map((v, i) => ({ x: data.labels[i], y: v })),
        color: color,
        stroke: { dashArray: dashArray }
      };
    });

    const options = {
      chart: {
        type: 'line',
        height: 400,
        zoom: { enabled: true },
        toolbar: { show: true },
        foreColor: textColor,
        background: 'transparent'
      },
      series: series,
      xaxis: {
        type: 'datetime',
        labels: { datetimeUTC: false, style: { colors: mutedColor } }
      },
      yaxis: {
        labels: {
          style: { colors: mutedColor },
          formatter: (value) => Number(value).toFixed(2)
        },
        title: { text: 'Base 100' }
      },
      stroke: {
        curve: 'smooth',
        width: 2
      },
      grid: {
        borderColor: borderColor,
        strokeDashArray: 3
      },
      annotations: {
        xaxis: annotations.map(a => ({
          x: new Date(a.date).getTime(),
          strokeDashArray: 0,
          borderColor: '#B42318',
          label: {
            text: a.label,
            style: {
              background: '#011D25',
              color: '#E8FFFD'
            }
          }
        }))
      },
      theme: {
        mode: isDark ? 'dark' : 'light'
      },
      tooltip: {
        x: { format: 'yyyy-MM-dd' },
        y: { formatter: (value) => Number(value).toFixed(2) }
      }
    };

    if (chart) {
      chart.updateOptions(options);
      chart.updateSeries(series);
    } else {
      chart = new ApexCharts(chartEl, options);
      chart.render();
    }
  }

  function renderTable(data) {
    if (!data.series.length) {
      perfTableEl.innerHTML = '<p class="text-text-muted text-sm">Aucune donnée.</p>';
      return;
    }
    let html = `
      <div class="overflow-x-auto mt-4">
        <table class="table-base">
          <thead>
            <tr><th>Instrument</th><th>Performance sur la période</th></tr>
          </thead>
          <tbody>
    `;
    data.series.forEach(s => {
      html += `
        <tr>
          <td class="py-2 pr-4">${s.name}</td>
          <td class="py-2 pr-4 ${s.performance_pct >= 0 ? 'text-positive' : 'text-negative'}">${formatPercent(s.performance_pct)}</td>
        </tr>
      `;
    });
    html += '</tbody></table></div>';
    perfTableEl.innerHTML = html;
  }

  periodSelect.addEventListener('change', loadData);
  container.querySelectorAll('.series-checkbox').forEach(cb => cb.addEventListener('change', loadData));

  document.addEventListener('themechange', (e) => {
    const newIsDark = e.detail.isDark;
    if (chart) {
      chart.updateOptions({ theme: { mode: newIsDark ? 'dark' : 'light' } });
    }
  });

  loadData();
}