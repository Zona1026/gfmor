export const isAdminTheme = value => value === 'dark' || value === 'light';
export const adminThemeKey = username => `gf.admin-theme:${encodeURIComponent(username)}`;
export const isAdminThemeRoute = path => path === '/admin' || path.startsWith('/admin/');

export function cachedAdminTheme(storage, username) {
  try {
    const value = storage?.getItem(adminThemeKey(username));
    return isAdminTheme(value) ? value : 'dark';
  } catch { return 'dark'; }
}

export function applyAdminTheme(theme) {
  if (isAdminTheme(theme)) document.documentElement.dataset.adminTheme = theme;
  else document.documentElement.removeAttribute('data-admin-theme');
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = theme === 'light' ? '#B4AB9B' : '#1e1e1e';
}

// Keep persistence independent of Vue so account changes and late responses can
// be tested without rendering an application or writing to a real account.
export function createAdminThemeController({ state, storage, apply, read, write, saved }) {
  let session = null, generation = 0, failedAction = null;
  function persist(theme) {
    try { storage?.setItem(adminThemeKey(session.username), theme); } catch { /* Account storage remains authoritative. */ }
    saved(session.username, theme);
  }
  async function activate(context, force = false) {
    const nextSession = context.inAdmin && context.username && context.token ? context : null;
    if (!force && nextSession && session?.username === nextSession.username && session?.token === nextSession.token) return;
    const current = ++generation;
    session = nextSession;
    state.saving = false;
    state.loading = false;
    state.error = '';
    failedAction = null;
    if (!session) { state.theme = 'dark'; apply(null); return; }
    state.theme = isAdminTheme(context.preferredTheme) ? context.preferredTheme : cachedAdminTheme(storage, context.username);
    apply(state.theme);
    state.loading = true;
    try {
      const response = await read(context.token);
      if (current !== generation) return;
      if (!isAdminTheme(response.theme)) throw new Error('Invalid theme preference');
      state.theme = response.theme;
      persist(response.theme);
      apply(response.theme);
    } catch {
      if (current !== generation) return;
      state.error = '主題偏好同步失敗，目前使用本機記錄。';
      failedAction = { type: 'read' };
    } finally { if (current === generation) state.loading = false; }
  }
  async function setTheme(theme) {
    if (!session || state.saving || state.loading || !isAdminTheme(theme) || theme === state.theme) return;
    const current = generation, previous = state.theme, token = session.token;
    state.saving = true;
    state.error = '';
    failedAction = null;
    state.theme = theme;
    apply(theme);
    try {
      const response = await write(theme, token);
      if (current !== generation) return;
      if (response.theme !== theme) throw new Error('Theme preference was not saved');
      persist(theme);
    } catch {
      if (current !== generation) return;
      state.theme = previous;
      apply(previous);
      state.error = '主題儲存失敗，已還原原本外觀，請重試。';
      failedAction = { type: 'write', theme };
    } finally { if (current === generation) state.saving = false; }
  }
  function retry() {
    if (!session || state.saving || state.loading) return;
    return failedAction?.type === 'write' ? setTheme(failedAction.theme) : activate(session, true);
  }
  return { activate, setTheme, retry };
}
