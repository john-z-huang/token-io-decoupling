#!/usr/bin/env node
// Use an existing Pi installation; never download dependencies or alter its configuration.
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { declarationPath, discoverPiHostRoot, openPiHost } from './pi-installed-host.mjs';

const project = fileURLToPath(new URL('../', import.meta.url));
const host = openPiHost(discoverPiHostRoot());
const typebox = declarationPath(host.requireHost.resolve('typebox'));
const temp = mkdtempSync(join(tmpdir(), 'pi-extension-types-'));
try {
  writeFileSync(
    join(temp, 'tsconfig.json'),
    JSON.stringify({
      compilerOptions: {
        target: 'ES2023',
        module: 'NodeNext',
        moduleResolution: 'NodeNext',
        allowImportingTsExtensions: true,
        noEmit: true,
        strict: true,
        skipLibCheck: true,
        types: ['node'],
        typeRoots: [join(host.root, 'node_modules/@types')],
        paths: {
          '@earendil-works/pi-coding-agent': [join(host.root, 'dist/index.d.ts')],
          typebox: [typebox],
        },
      },
      include: [join(project, 'extensions/**/*.ts')],
    }),
  );
  const result = spawnSync(process.env.TSC_BIN ?? 'tsc', ['-p', join(temp, 'tsconfig.json')], {
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exitCode = result.status ?? 1;
  else console.log(`Pi ${host.version} 宿主声明类型检查通过（不代表真实客户端验收）`);
} finally {
  rmSync(temp, { recursive: true, force: true });
}
