// Read-only dependency-resolution diagnostics, only inside the offline sandbox.
import fs from 'node:fs'
import { createRequire } from 'node:module'
if (process.env.DASH_FULL_OFFLINE_SANDBOX !== '1') throw Error('Use isolated launcher')
const require = createRequire('/source/my-app/package.json')
for (const name of ['react', 'prop-types', 'react-markdown']) {
  const base = '/source/my-app/node_modules/' + name
  for (const file of [base, base + '/package.json']) {
    try { console.log('FILE', file, fs.statSync(file).isDirectory(), fs.realpathSync(file)) }
    catch (error) { console.log('FILE_ERROR', file, error.code) }
  }
  try { console.log('NODE_RESOLVE', name, require.resolve(name)) }
  catch (error) { console.log('NODE_RESOLVE_ERROR', name, error.code) }
}
const { resolveConfig } = await import('/source/my-app/node_modules/vite/dist/node/index.js')
const config = await resolveConfig({ configFile: '/source/my-app/vite.config.ts', configLoader: 'runner' }, 'build')
const resolver = config.createResolver()
for (const name of ['react', 'prop-types', 'react-markdown']) {
  try { console.log('VITE_RESOLVE', name, await resolver(name, '/source/my-app/src/reports/ReportDetail.jsx')) }
  catch (error) { console.log('VITE_RESOLVE_ERROR', name, error.code, error.message) }
}
