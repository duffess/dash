// Same production build, with bounded file concurrency for the offline sandbox.
if (process.env.DASH_FULL_OFFLINE_SANDBOX !== '1') throw Error('Use isolated launcher')
const { build } = await import('/source/my-app/node_modules/vite/dist/node/index.js')
await build({
  configFile: '/source/my-app/vite.config.ts',
  configLoader: 'runner',
  build: { outDir: '/scratch/dist', emptyOutDir: true, rollupOptions: { maxParallelFileOps: 32 } },
})
