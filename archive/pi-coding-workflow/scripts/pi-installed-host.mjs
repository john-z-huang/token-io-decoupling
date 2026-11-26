import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const PI_PACKAGE = '@earendil-works/pi-coding-agent';

// 只有允许本地解析的检查入口才调用此函数。显式插件检查直接使用 openPiHost。
export function discoverPiHostRoot() {
  const configuredRoot = process.argv[2] ?? process.env.PI_EXTENSION_HOST_ROOT;
  if (configuredRoot) return configuredRoot;
  try {
    const entry = createRequire(import.meta.url).resolve(PI_PACKAGE);
    return dirname(dirname(entry));
  } catch {
    console.error('请传已有 Pi 包根目录，或设置 PI_EXTENSION_HOST_ROOT；不自动安装依赖。');
    process.exit(2);
  }
}

export function openPiHost(location) {
  const root = resolve(location);
  const packagePath = join(root, 'package.json');
  const metadata = JSON.parse(readFileSync(packagePath, 'utf8'));
  assert.equal(metadata.name, PI_PACKAGE, '不是 Pi Coding Agent 包根目录');
  return { root, version: metadata.version, requireHost: createRequire(packagePath) };
}

export function hostModulePaths(host) {
  const modules = {
    [PI_PACKAGE]: join(host.root, 'dist/index.js'),
    typebox: host.requireHost.resolve('typebox'),
  };
  for (const name of ['pi-ai', 'pi-agent-core', 'pi-tui']) {
    const scopedName = `@earendil-works/${name}`;
    modules[scopedName] = join(host.root, 'node_modules', scopedName, 'dist/index.js');
  }
  return modules;
}

export function declarationPath(path) {
  return path.replace(/\.mjs$/, '.d.mts').replace(/\.js$/, '.d.ts');
}

export function createHostLoader(host, from, alias) {
  const { createJiti } = host.requireHost('jiti');
  return createJiti(from, { moduleCache: false, fsCache: false, alias });
}

export async function loadTypeBoxCheck(host) {
  const url = pathToFileURL(host.requireHost.resolve('typebox/value'));
  const valueModule = await import(url.href);
  const check = valueModule.Value?.Check ?? valueModule.Check;
  assert.equal(typeof check, 'function');
  return check;
}
