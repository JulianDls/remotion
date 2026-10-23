import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
// Renderizador OpenGL: por defecto lo decide Chrome (la intro no usa WebGL).
// Se puede forzar con REMOTION_GL=swangle|angle|swiftshader|egl.
const gl = process.env.REMOTION_GL;
if (gl) {
	Config.setChromiumOpenGlRenderer(gl as Parameters<typeof Config.setChromiumOpenGlRenderer>[0]);
}
const exe = process.env.REMOTION_BROWSER_EXECUTABLE;
if (exe) {
	Config.setBrowserExecutable(exe);
}
