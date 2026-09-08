import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const directory = path.dirname(fileURLToPath(import.meta.url));
const stems = [
  'proposal_to_replication.workflow',
  'reproducibility_map.architecture',
  'programme_timeline.architecture',
  'registration_seals.workflow',
  'proposal_to_replication_readme.workflow',
];
const compactStems = new Set([
  'proposal_to_replication_readme.workflow',
  'programme_timeline.architecture',
]);
const hash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const manifestPath = path.join(directory, 'manifest.json');
const mode = process.argv[2] || '--verify';
assert(['--verify', '--render', '--export', '--contact-sheets'].includes(mode), 'Unknown mode');
const requested = process.argv.slice(3);
assert(requested.every(stem => stems.includes(stem)), 'Unknown diagram name');
assert(mode !== '--verify' || requested.length === 0, 'Verification always checks every diagram');
const selected = requested.length ? requested : stems;

// The narrow README diagrams need a narrower standalone reader on desktop.
// Preserve the delivered native HTML separately; this display derivative changes
// only its outer reading width. It never crops or changes SVG geometry or fonts.
function fitReaderToViewport(html) {
  assert(html.includes('</body>'), 'The delivered reader has no body');
  const adapter = `<script id="readme-reader-fit">
  (function () {
    var queued = false;
    function fit() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () {
        queued = false;
        var shell = document.querySelector('.container');
        if (!shell) return;
        if (window.innerWidth < 900) {
          shell.style.removeProperty('max-width');
          return;
        }
        var low = 300;
        var high = window.innerWidth - 64;
        var best = low;
        for (var attempt = 0; attempt < 16; attempt += 1) {
          var width = (low + high) / 2;
          shell.style.setProperty('max-width', width + 'px', 'important');
          if (document.documentElement.scrollHeight <= window.innerHeight) {
            best = width;
            low = width;
          } else high = width;
        }
        // Navigation controls finish mounting after first layout. Preserve room
        // for their measured 41–51px height without changing diagram content.
        var svg = shell.querySelector('svg');
        var box = svg && svg.viewBox.baseVal;
        var reserve = box && box.height ? 72 * box.width / box.height : 72;
        shell.style.setProperty('max-width', Math.floor(Math.max(300, best - reserve)) + 'px', 'important');
      });
    }
    window.addEventListener('load', fit);
    window.addEventListener('resize', fit);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
    var shell = document.querySelector('.container');
    if (shell && window.ResizeObserver) {
      new ResizeObserver(function () {
        if (document.documentElement.scrollHeight > window.innerHeight) fit();
      }).observe(shell);
    }
    fit();
  })();
  </script>`;
  return html.replace('</body>', `${adapter}\n</body>`);
}

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
    for (const stem of selected) {
      const source = path.join(directory, `${stem}.json`);
      const html = path.join(directory, `${stem}.html`);
      const type = JSON.parse(fs.readFileSync(source, 'utf8')).diagram_type;
      if (mode === '--render') {
        command('validate', type, source, '--quality', 'showcase');
        const nativeHtml = compactStems.has(stem)
          ? path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'readme-archify-')), `${stem}.html`)
          : html;
        const receipt = command('deliver', type, source, nativeHtml, '--quality', 'showcase');
        assert.equal(receipt.validation.checksPassed, 9);
        assert.equal(receipt.validation.errors, 0);
        assert.equal(receipt.validation.warnings, 0);
        if (nativeHtml !== html) {
          fs.writeFileSync(html, fitReaderToViewport(fs.readFileSync(nativeHtml, 'utf8')));
        }
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
        let svg = result.result.value.svg;
        assert(svg.includes('<svg') && !svg.includes('<script'), 'Invalid static SVG export');
        if (compactStems.has(stem)) {
          // GitHub constrains wide images but does not upscale a small intrinsic
          // canvas. Keep the native viewBox and set a 2x README intrinsic width.
          const opening = svg.match(/<svg\b[^>]*>/)[0];
          const box = opening.match(/\bviewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
          assert(box.length === 4 && box[2] > 0 && box[3] > 0);
          const resized = opening.replace(/\bwidth="[^"]+"/, 'width="1662"')
            .replace(/\bheight="[^"]+"/, `height="${1662 * box[3] / box[2]}"`);
          assert(resized !== opening, 'Compact intrinsic canvas was not resized');
          svg = svg.replace(opening, resized);
        }
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
  assert.deepEqual(
    manifest.diagrams.map(diagram => diagram.source.path).sort(),
    stems.map(stem => `${stem}.json`).sort(),
    'Manifest must contain exactly the five versioned diagram sources',
  );
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
  assert.equal(checked, 15, 'Expected five sources, five HTML files and five SVG files');
  console.log(`Verified ${checked} artifact hashes and byte counts.`);
}
