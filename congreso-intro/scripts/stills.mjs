// Renderiza fotogramas de control (QA) en una sola sesión de navegador.
// Uso: node scripts/stills.mjs <salida_dir> <seg1> <seg2> ...   (REMOTION_BROWSER_EXECUTABLE opcional)
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition, openBrowser} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const [outDir, ...secs] = process.argv.slice(2);
fs.mkdirSync(outDir, {recursive: true});
const scale = Number(process.env.STILL_SCALE ?? '0.5');
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), onProgress: () => {}});
const browser = await openBrowser('chrome', {
	browserExecutable: process.env.REMOTION_BROWSER_EXECUTABLE ?? null,
	chromiumOptions: {gl: 'swangle'},
});
const composition = await selectComposition({serveUrl, id: 'Intro', puppeteerInstance: browser});
for (const s of secs) {
	const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(s) * composition.fps));
	const out = path.join(outDir, `f_${String(s).replace('.', '_')}.jpg`);
	const t0 = Date.now();
	await renderStill({composition, serveUrl, frame, output: out, imageFormat: 'jpeg', jpegQuality: 88, scale, puppeteerInstance: browser});
	console.log(`${s}s -> ${out} (${Date.now() - t0} ms)`);
}
await browser.close({silent: true});
