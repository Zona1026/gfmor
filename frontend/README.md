# Vue 3 + Vite

## Node.js version

Use Node.js 20.20.2, pinned in the repository's `.node-version`. GitHub Actions and Render use this file for consistent builds. The Windows Node.js 24.12.0 runtime can terminate during production builds with exit code `0xC0000409`.

If the local default Node.js version differs, build with the pinned runtime without changing the system installation:

```powershell
npx --yes --package=node@20.20.2 -c "npm run build"
```

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).
