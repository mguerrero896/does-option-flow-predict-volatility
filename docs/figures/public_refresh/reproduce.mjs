import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const directory = path.dirname(fileURLToPath(import.meta.url));
const stems = [
  'proposal_to_replication.workflow',
  'reproducibility_map.architecture',
  'programme_timeline.architecture',
  'registration_seals.workflow',
];
const hash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const manifestPath = path.join(directory, 'manifest.json');
const mode = process.argv[2] || '--verify';
assert(['--verify', '--render', '--export', '--contact-sheets'].includes(mode), 'Unknown mode');

if (mode !== '--verify') {
  assert(process.env.ARCHIFY_HOME, 'Set ARCHIFY_HOME to an existing Archify 2.16 skill directory.');
  const skill = path.resolve(process.env.ARCHIFY_HOME);
  const command = (...args) => {
    const result = spawnSync(process.execPath, [path.join(skill, 'bin/archify.mjs'), ...args, '--json'], {
      encoding: 'utf8', maxBuffer: 4 * 1024 * 1024,
    });
    if (result.error) throw result.error;
    assert.equal(result.status, 0, `${args[0]} failed: ${result.stdout}\n${result.stderr}`);
    return JSON.parse(result.stdout);
  };
  const { ChromeVisualBrowser, findChrome } = await import(pathToFileURL(path.join(skill, 'bin/visual-check.mjs')));
  const chrome = findChrome();
  assert(chrome, 'Chrome or Chromium is required for canonical SVG export and visual evidence.');
  const browser = new ChromeVisualBrowser(chrome);
  try {
    const sessionId = await browser.sessionPromise;
    await browser.cdp.send('Browser.setDownloadBehavior', { behavior: 'deny' });
    for (const stem of stems) {
      const source = path.join(directory, `${stem}.json`);
      const html = path.join(directory, `${stem}.html`);
      const type = stem.split('.').at(-1);
      if (mode === '--render') {
        command('validate', type, source, '--quality', 'showcase');
        const receipt = command('deliver', type, source, html, '--quality', 'showcase');
        assert.equal(receipt.validation.checksPassed, 9);
        assert.equal(receipt.validation.errors, 0);
        assert.equal(receipt.validation.warnings, 0);
        command('visual-check', html);
      }
      if (mode === '--contact-sheets') {
        await browser.inspect({ artifactPath: path.join(directory, `${stem}.visual-check.html`),
          width: 1600, height: 1250, theme: 'light',
          screenshotPath: path.join(directory, `${stem}.visual-check.contact.png`) });
      } else {
        await browser.inspect({ artifactPath: html, width: 1440, height: 900, theme: 'light' });
        const result = await browser.cdp.send('Runtime.evaluate', {
          expression: `(async function () {
            const original = URL.createObjectURL;
            let captured;
            URL.createObjectURL = function (blob) { captured = blob; return original.call(URL, blob); };
            try { await Archify.exportMenu.run('svg'); } finally { URL.createObjectURL = original; }
            if (!captured) throw new Error('Native SVG exporter produced no artifact');
            return { svg: await captured.text(),
              canonical: document.documentElement.getAttribute('data-last-export-canonical') };
          })()`, awaitPromise: true, returnByValue: true,
        }, sessionId);
        assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
        assert.equal(result.result.value.canonical, 'true');
        const svg = result.result.value.svg;
        assert(svg.includes('<svg') && !svg.includes('<script'), 'Invalid static SVG export');
        fs.writeFileSync(path.join(directory, `${stem}.svg`), `${svg}\n`);
      }
      console.log(`${stem}: ${mode.slice(2)} passed`);
    }
  } finally {
    await browser.close();
  }
}

if (mode === '--verify') {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  let checked = 0;
  for (const diagram of manifest.diagrams) {
    for (const artifact of [diagram.source, diagram.html, diagram.svg]) {
      assert.equal(path.basename(artifact.path), artifact.path, 'Manifest paths must be local filenames');
      const file = path.join(directory, artifact.path);
      assert.equal(hash(file), artifact.sha256, `Hash mismatch: ${artifact.path}`);
      assert.equal(fs.statSync(file).size, artifact.bytes, `Size mismatch: ${artifact.path}`);
      checked += 1;
    }
  }
  assert.equal(checked, 12, 'Expected four sources, four HTML files and four SVG files');
  console.log(`Verified ${checked} artifact hashes and byte counts.`);
}
