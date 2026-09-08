'use strict';

// Rasterize a supplied SVG only; no network, fonts download, or external metadata.
const sharp = require(process.argv[2]);
sharp.concurrency(1);
const chunks = [];
process.stdin.on('data', chunk => chunks.push(chunk));
process.stdin.on('end', async () => {
  try {
    const input = Buffer.concat(chunks);
    const {data, info} = await sharp(input, {density: 96})
      .png({compressionLevel: 9, adaptiveFiltering: false, palette: false})
      .toBuffer({resolveWithObject: true});
    process.stdout.write(data);
    process.stderr.write(JSON.stringify({
      sharp: sharp.versions.sharp,
      vips: sharp.versions.vips,
      width: info.width,
      height: info.height,
      format: info.format,
      renderer_threads: 1,
      density: 96,
      metadata_copied: false,
    }));
  } catch (error) {
    process.stderr.write(String(error));
    process.exitCode = 1;
  }
});
