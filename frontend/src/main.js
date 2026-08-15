import './style.css';
import { createIcons, icons } from 'lucide';
import Handlebars from 'handlebars';
import { renderDashboard } from './views/dashboard.js';
import { renderEtfs } from './views/etfs.js';
import { renderSignals } from './views/signals.js';
import { renderSettings } from './views/settings.js';
import { renderLogin } from './views/login.js';

// Helper Handlebars pour les comparaisons dans les templates
Handlebars.registerHelper('eq', (a, b) => a === b);

// Thème
function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = saved === 'dark' || (!saved && prefersDark);
  if (isDark) {
    document.documentElement.classList.add('dark');
  }
  document.dispatchEvent(new CustomEvent('themechange', { detail: { isDark } }));
}

function toggleTheme() {
  document.documentElement.classList.toggle('dark');
  const isDark = document.documentElement.classList.contains('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  const label = document.getElementById('theme-label');
  if (label) label.textContent = isDark ? 'Mode clair' : 'Mode sombre';
  document.dispatchEvent(new CustomEvent('themechange', { detail: { isDark } }));
  refreshIcons();
}

function refreshIcons() {
  createIcons({
    icons: {
      LayoutDashboard: icons.LayoutDashboard,
      FolderCog: icons.FolderCog,
      Settings: icons.Settings,
      Moon: icons.Moon,
      Sun: icons.Sun,
      RefreshCw: icons.RefreshCw,
      Plus: icons.Plus,
      Upload: icons.Upload,
      Pencil: icons.Pencil,
      Trash2: icons.Trash2,
      AlertTriangle: icons.AlertTriangle,
      Check: icons.Check,
      X: icons.X,
      Info: icons.Info,
      CalendarClock: icons.CalendarClock,
      Calculator: icons.Calculator,
      Sparkles: icons.Sparkles,
      LogOut: icons.LogOut
    }
  });
}

const routes = {
  '/dashboard': renderDashboard,
  '/etfs': renderEtfs,
  '/signals': renderSignals,
  '/settings': renderSettings,
  '/login': renderLogin
};

function parseRoute() {
  const hash = window.location.hash.slice(1);
  if (!hash) return '/dashboard';
  return hash.startsWith('/') ? hash : `/${hash}`;
}

function isAuthenticated() {
  return !!localStorage.getItem('access_token');
}

function isAdmin() {
  return localStorage.getItem('is_admin') === 'true';
}

async function router() {
  const path = parseRoute();
  const render = routes[path] || routes['/dashboard'];
  const container = document.getElementById('view-container');

  // Si la route n'est pas login et pas authentifié -> rediriger vers login
  if (path !== '/login' && !isAuthenticated()) {
    window.location.hash = '#/login';
    return;
  }

  // Si déjà authentifié et sur login -> aller au dashboard
  if (path === '/login' && isAuthenticated()) {
    window.location.hash = '#/dashboard';
    return;
  }

  // Bloquer l'accès aux paramètres pour les non-admin
  if (path === '/settings' && !isAdmin()) {
    window.location.hash = '#/dashboard';
    return;
  }

  // Masquer le lien Paramètres pour les non-admin
  document.querySelectorAll('[data-route="/settings"]').forEach(link => {
    link.style.display = isAdmin() ? '' : 'none';
  });

  // Mise à jour des liens actifs
  document.querySelectorAll('[data-route]').forEach((link) => {
    link.classList.toggle('active', link.dataset.route === path);
  });

  await render(container);
  refreshIcons();
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  router();

  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
});

window.addEventListener('hashchange', router);

// Gestion de la déconnexion
document.addEventListener('click', (e) => {
  if (e.target.closest('#logout-btn')) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('is_admin');
    window.location.hash = '#/login';
  }
});