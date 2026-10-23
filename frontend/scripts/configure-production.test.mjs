import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkConfig,productionConfig} from './configure-production.mjs';

test('API routing precedes SPA fallback, remains same-origin, and disables caching', () => {
  const config = productionConfig('https://sprintlens-api.onrender.com');
  assert.equal(config.rewrites[0].source,'/api/:path(.*)');
  assert.equal(config.rewrites[0].destination,'https://sprintlens-api.onrender.com/api/:path');
  assert.equal(config.rewrites[1].destination,'/index.html');
  assert.ok(config.headers[1].headers.some(h => h.key === 'Vercel-CDN-Cache-Control' && h.value === 'no-store'));
  assert.ok(config.headers[0].headers.some(h => h.key === 'Content-Security-Policy' && h.value.includes("connect-src 'self'")));
  assert.doesNotThrow(() => checkConfig(config));
});

test('reject accidental HTTP, secret-bearing URLs, placeholders and embedded API paths', () => {
  for(const origin of ['http://api.example.com','https://name:password@api.example.com','https://api.example.com/api','https://api.example.com?token=secret','https://api.example.com#fragment','https://api.example.invalid','https://localhost','https://127.0.0.1',undefined]) {
    assert.throws(() => productionConfig(origin));
  }
});

test('custom HTTPS origins normalize one trailing slash; edited config is detected', () => {
  const config = productionConfig('https://api.sprintlens.test/');
  assert.equal(config.rewrites[0].destination,'https://api.sprintlens.test/api/:path');
  config.rewrites.reverse();
  assert.throws(() => checkConfig(config));
});
