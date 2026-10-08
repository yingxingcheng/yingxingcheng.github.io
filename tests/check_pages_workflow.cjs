// Exercise the exact github-script code without contacting GitHub or waiting.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('.github/workflows/monthly-build.yml', 'utf8');
const script = source.split('          script: |\n')[1]
  .split('\n').map(line => line.startsWith('            ') ? line.slice(12) : line).join('\n');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const run = new AsyncFunction('github', 'context', 'core', 'process', 'setTimeout', script);
const sha = 'expected-commit';

async function scenario(builds, expectedRequests, errorPattern) {
  let requests = 0;
  let reads = 0;
  const github = {rest: {repos: {
    async getLatestPagesBuild() {
      const item = builds[Math.min(reads++, builds.length - 1)];
      if (item === null) throw Object.assign(new Error('missing'), {status: 404});
      return {data: item};
    },
    async requestPagesBuild() { requests++; },
  }}};
  const action = run(github, {repo: {owner: 'owner', repo: 'repo'}}, {info() {}},
    {env: {EXPECTED_SHA: sha}}, resolve => resolve());
  if (errorPattern) await assert.rejects(action, errorPattern);
  else await action;
  assert.equal(requests, expectedRequests);
}

(async () => {
  await scenario([{commit: sha, status: 'built'}], 0);
  await scenario([null, {commit: sha, status: 'queued'}, {commit: sha, status: 'built'}], 1);
  await scenario([{commit: 'old', status: 'built'}, {commit: sha, status: 'built'}], 1);
  await scenario([{commit: sha, status: 'errored'}, {commit: sha, status: 'built'}], 1);
  await scenario([null, {commit: sha, status: 'errored', error: {message: 'build failed'}}], 1, /build failed/);
  await scenario([{commit: 'old', status: 'built'}], 1, /Timed out/);
  console.log('6 Pages workflow regression scenarios passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
