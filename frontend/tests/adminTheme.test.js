import assert from 'node:assert/strict';
import test from 'node:test';
import { adminThemeKey, cachedAdminTheme, createAdminThemeController, isAdminThemeRoute } from '../src/utils/adminTheme.js';

const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function harness() {
  const state = { theme: 'dark', saving: false, loading: false, error: '' };
  const values = new Map(), reads = [], writes = [], applied = [], saved = [];
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) };
  const controller = createAdminThemeController({
    state, storage, apply: value => applied.push(value), saved: (...args) => saved.push(args),
    read: token => { const pending = deferred(); reads.push({ token, ...pending }); return pending.promise; },
    write: (theme, token) => { const pending = deferred(); writes.push({ theme, token, ...pending }); return pending.promise; },
  });
  const session = (username = 'a', token = `token-${username}`) => ({ username, token, inAdmin: true });
  const activate = async (username = 'a', theme = 'dark') => {
    const pending = controller.activate(session(username));
    reads.at(-1).resolve({ theme });
    await pending;
  };
  return { state, storage, values, reads, writes, applied, saved, controller, session, activate };
}

test('theme applies only to authenticated back-office routes', async () => {
  assert.equal(isAdminThemeRoute('/admin'), true);
  assert.equal(isAdminThemeRoute('/admin/work-orders'), true);
  for (const path of ['/', '/products', '/admin-login', '/admin-reset-password', '/administrator']) assert.equal(isAdminThemeRoute(path), false);
  const h = harness();
  await h.controller.activate({ ...h.session(), inAdmin: false });
  assert.equal(h.reads.length, 0);
  assert.equal(h.applied.at(-1), null);
});

test('account preference overrides its local cache and remains separate from other accounts', async () => {
  const h = harness();
  h.values.set(adminThemeKey('a'), 'dark');
  h.values.set(adminThemeKey('b'), 'light');
  await h.activate('a', 'light');
  assert.equal(h.state.theme, 'light');
  assert.equal(h.values.get(adminThemeKey('a')), 'light');
  await h.activate('b', 'dark');
  assert.equal(h.state.theme, 'dark');
  assert.equal(h.values.get(adminThemeKey('a')), 'light');
  assert.equal(h.values.get(adminThemeKey('b')), 'dark');
});

test('login preference is applied before the server refresh completes', async () => {
  const h = harness();
  const pending = h.controller.activate({ ...h.session(), preferredTheme: 'light' });
  assert.equal(h.applied[0], 'light');
  assert.equal(h.state.loading, true);
  h.reads[0].resolve({ theme: 'light' });
  await pending;
});

test('successful changes preview immediately and persist using the captured account token', async () => {
  const h = harness();
  await h.activate();
  const pending = h.controller.setTheme('light');
  assert.equal(h.state.theme, 'light');
  assert.equal(h.state.saving, true);
  assert.equal(h.writes[0].token, 'token-a');
  assert.equal(h.values.get(adminThemeKey('a')), 'dark');
  h.writes[0].resolve({ theme: 'light' });
  await pending;
  assert.equal(h.values.get(adminThemeKey('a')), 'light');
  assert.equal(h.state.saving, false);
});

test('failed writes restore the confirmed theme and can retry the requested choice', async () => {
  const h = harness();
  await h.activate();
  const pending = h.controller.setTheme('light');
  h.writes[0].reject(new Error('Offline'));
  await pending;
  assert.equal(h.state.theme, 'dark');
  assert.equal(h.values.get(adminThemeKey('a')), 'dark');
  assert.match(h.state.error, /儲存失敗/);
  const retry = h.controller.retry();
  assert.equal(h.writes[1].theme, 'light');
  h.writes[1].resolve({ theme: 'light' });
  await retry;
  assert.equal(h.state.theme, 'light');
  assert.equal(h.state.error, '');
});

test('late reads from an older account cannot overwrite the current account', async () => {
  const h = harness();
  const first = h.controller.activate(h.session('a'));
  const second = h.controller.activate(h.session('b'));
  h.reads[1].resolve({ theme: 'dark' });
  await second;
  h.reads[0].resolve({ theme: 'light' });
  await first;
  assert.equal(h.state.theme, 'dark');
  assert.deepEqual(h.saved, [['b', 'dark']]);
});

test('logout cancels pending UI updates and an old save cannot affect a different login', async () => {
  const h = harness();
  await h.activate();
  const saving = h.controller.setTheme('light');
  await h.controller.activate({ inAdmin: false });
  assert.equal(h.applied.at(-1), null);
  await h.activate('b');
  h.writes[0].resolve({ theme: 'light' });
  await saving;
  assert.equal(h.state.theme, 'dark');
  assert.equal(h.values.get(adminThemeKey('b')), 'dark');
  assert.equal(h.values.get(adminThemeKey('a')), 'dark');
});

test('unavailable storage and invalid cached values default safely to dark', () => {
  assert.equal(cachedAdminTheme(undefined, 'a'), 'dark');
  assert.equal(cachedAdminTheme({ getItem: () => 'system' }, 'a'), 'dark');
  assert.equal(cachedAdminTheme({ getItem() { throw new Error('Denied'); } }, 'a'), 'dark');
});

test('a read failure keeps the cached appearance and retries without blocking the application', async () => {
  const h = harness();
  h.values.set(adminThemeKey('a'), 'light');
  const pending = h.controller.activate(h.session());
  h.reads[0].reject(new Error('Offline'));
  await pending;
  assert.equal(h.state.theme, 'light');
  assert.equal(h.state.loading, false);
  const retry = h.controller.retry();
  h.reads[1].resolve({ theme: 'dark' });
  await retry;
  assert.equal(h.state.theme, 'dark');
});

test('duplicate, invalid and pending changes do not send extra writes', async () => {
  const h = harness();
  await h.activate();
  await h.controller.setTheme('dark');
  await h.controller.setTheme('unknown');
  const pending = h.controller.setTheme('light');
  await h.controller.setTheme('dark');
  assert.equal(h.writes.length, 1);
  h.writes[0].resolve({ theme: 'light' });
  await pending;
  await h.controller.activate(h.session());
  assert.equal(h.reads.length, 1);
});
