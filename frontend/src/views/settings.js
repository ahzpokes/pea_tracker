import { api } from '../api/client.js';

export async function renderSettings(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <h1 class="text-2xl font-semibold">Paramètres</h1>
      <div id="settings-content"></div>
    </div>
  `;

  const content = document.getElementById('settings-content');
  content.innerHTML = '<p class="text-text-muted text-sm">Chargement…</p>';

  try {
    const [settings, users] = await Promise.all([
      api.get('/settings'),
      api.get('/auth/users')
    ]);

    const settingsMap = {};
    settings.forEach(s => {
      settingsMap[s.setting_key] = s.setting_value;
    });

    content.innerHTML = `
      <form id="settings-form" class="space-y-6">
        <div class="card">
          <h2 class="text-lg font-medium mb-4">Intelligence Artificielle</h2>
          <p class="text-sm text-text-muted mb-4">Configurez le fournisseur d'IA utilisé pour générer les commentaires pédagogiques. Les calculs financiers restent toujours effectués par Python.</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="label" for="ai-provider">Fournisseur IA</label>
              <select id="ai-provider" class="input">
                <option value="local" ${settingsMap['AI_PROVIDER'] === 'local' ? 'selected' : ''}>Local (sans API)</option>
                <option value="gemini" ${settingsMap['AI_PROVIDER'] === 'gemini' ? 'selected' : ''}>Google Gemini</option>
                <option value="nvidia" ${settingsMap['AI_PROVIDER'] === 'nvidia' ? 'selected' : ''}>NVIDIA</option>
              </select>
            </div>
            <div>
              <label class="label" for="ai-model">Modèle</label>
              <input id="ai-model" class="input" placeholder="ex: gemini-2.0-flash" value="${settingsMap['AI_MODEL'] || ''}" />
              <p class="text-xs text-text-muted mt-1">Laissez vide pour utiliser le modèle par défaut du fournisseur.</p>
            </div>
            <div id="gemini-key-wrapper">
              <label class="label" for="gemini-key">Clé API Gemini</label>
              <input id="gemini-key" type="password" class="input" placeholder="AIza..." value="${settingsMap['GEMINI_API_KEY'] || ''}" autocomplete="off" />
            </div>
            <div id="nvidia-key-wrapper">
              <label class="label" for="nvidia-key">Clé API NVIDIA</label>
              <input id="nvidia-key" type="password" class="input" placeholder="nvapi-..." value="${settingsMap['NVIDIA_API_KEY'] || ''}" autocomplete="off" />
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button type="submit" class="btn btn-primary">Enregistrer les modifications</button>
          <span id="settings-message" class="text-sm"></span>
        </div>
      </form>

      <div class="card">
        <h2 class="text-lg font-medium mb-4">Comptes utilisateurs</h2>
        <div class="space-y-4">
          <div id="users-list" class="space-y-3">
            ${users.map(user => `
              <div class="flex items-center justify-between py-2 border-b border-border">
                <div>
                  <p class="font-medium">${user.username}</p>
                  <p class="text-xs text-text-muted">${user.is_admin ? 'Administrateur' : 'Utilisateur'} · Créé le ${new Date(user.created_at).toLocaleDateString('fr-FR')}</p>
                </div>
                ${user.username !== 'admin' ? `
                  <button class="btn btn-sm btn-danger delete-user-btn" data-user-id="${user.id}" data-username="${user.username}">
                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                    Supprimer
                  </button>
                ` : ''}
              </div>
            `).join('')}
          </div>

          <form id="user-form" class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="label" for="new-username">Nom d'utilisateur</label>
              <input id="new-username" class="input" required minlength="3" placeholder="ex: invité" />
            </div>
            <div>
              <label class="label" for="new-password">Mot de passe</label>
              <input id="new-password" type="password" class="input" required minlength="6" placeholder="6 caractères min." autocomplete="new-password" />
            </div>
            <div>
              <label class="flex items-center gap-2">
                <input id="new-is-admin" type="checkbox" class="rounded border-border" />
                <span class="text-sm">Administrateur</span>
              </label>
            </div>
            <div class="md:col-span-3 flex justify-end">
              <button type="submit" class="btn btn-primary">Créer le compte</button>
            </div>
          </form>
          <div id="user-message" class="text-sm"></div>
        </div>
      </div>
    `;

    // Gestion de la visibilité des champs clés API
    function updateVisibility() {
      const provider = document.getElementById('ai-provider').value;
      document.getElementById('gemini-key-wrapper').style.display = provider === 'gemini' ? 'block' : 'none';
      document.getElementById('nvidia-key-wrapper').style.display = provider === 'nvidia' ? 'block' : 'none';
    }
    updateVisibility();
    document.getElementById('ai-provider')?.addEventListener('change', updateVisibility);

    // Sauvegarde des paramètres IA
    document.getElementById('settings-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = [
        { setting_key: 'AI_PROVIDER', setting_value: document.getElementById('ai-provider').value },
        { setting_key: 'AI_MODEL', setting_value: document.getElementById('ai-model').value },
        { setting_key: 'GEMINI_API_KEY', setting_value: document.getElementById('gemini-key').value },
        { setting_key: 'NVIDIA_API_KEY', setting_value: document.getElementById('nvidia-key').value }
      ];
      const msgEl = document.getElementById('settings-message');
      msgEl.textContent = 'Enregistrement…';
      msgEl.className = 'text-sm';
      try {
        await api.patch('/settings', payload);
        msgEl.textContent = '✅ Paramètres enregistrés.';
        msgEl.className = 'text-sm text-positive';
      } catch (error) {
        msgEl.textContent = 'Erreur : ' + error.message;
        msgEl.className = 'text-sm text-negative';
      }
    });

    // Création d'un utilisateur
    document.getElementById('user-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('new-username').value;
      const password = document.getElementById('new-password').value;
      const isAdmin = document.getElementById('new-is-admin').checked;
      const msgEl = document.getElementById('user-message');
      msgEl.textContent = 'Création…';
      msgEl.className = 'text-sm';
      try {
        await api.post('/auth/users', { username, password, is_admin: isAdmin });
        msgEl.textContent = '✅ Compte créé.';
        msgEl.className = 'text-sm text-positive';
        // Rafraîchir la page
        renderSettings(container);
      } catch (error) {
        msgEl.textContent = 'Erreur : ' + error.message;
        msgEl.className = 'text-sm text-negative';
      }
    });

    // Suppression d'un utilisateur
    document.querySelectorAll('.delete-user-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = btn.dataset.userId;
        const username = btn.dataset.username;
        if (!confirm(`Supprimer le compte "${username}" ?`)) return;
        try {
          await api.delete(`/auth/users/${userId}`);
          renderSettings(container);
        } catch (error) {
          alert(error.message);
        }
      });
    });

  } catch (error) {
    content.innerHTML = `
      <div class="card border-negative/30 bg-negative/10 text-negative p-4">${error.message}</div>
    `;
  }
}