import { api } from '../api/client.js';

export async function renderLogin(container) {
  container.innerHTML = `
    <div class="min-h-screen flex items-center justify-center">
      <div class="w-full max-w-md">
        <div class="card p-8">
          <div class="flex justify-center mb-6">
            <!-- Logo SVG -->
            <svg width="48" height="48" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="18" cy="18" r="14" stroke="var(--teal)" stroke-width="2" stroke-dasharray="3 3" fill="none"/>
              <path d="M4 23 L10 18 L18 22 L26 10 L32 14" stroke="var(--navy)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M26 10 L26 16 L32 16" stroke="var(--teal)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1 class="text-2xl font-semibold text-center mb-6">Connexion</h1>
          <form id="login-form" class="space-y-4">
            <div>
              <label class="label" for="username">Nom d'utilisateur</label>
              <input id="username" class="input" required autocomplete="username" placeholder="admin" />
            </div>
            <div>
              <label class="label" for="password">Mot de passe</label>
              <input id="password" type="password" class="input" required autocomplete="current-password" placeholder="••••••••" />
            </div>
            <button type="submit" class="btn btn-primary w-full">Se connecter</button>
          </form>
          <div id="login-error" class="mt-4 text-sm text-negative text-center"></div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.textContent = '';
    try {
      const result = await api.post('/auth/login', { username, password });
      localStorage.setItem('access_token', result.access_token);
      localStorage.setItem('is_admin', result.is_admin ? 'true' : 'false');
      window.location.hash = '#/dashboard';
    } catch (error) {
      errorEl.textContent = error.message;
    }
  });
}