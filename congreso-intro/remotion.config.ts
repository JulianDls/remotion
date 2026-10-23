import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setChromiumOpenGlRenderer('swangle');
const exe = process.env.REMOTION_BROWSER_EXECUTABLE;
if (exe) {
	Config.setBrowserExecutable(exe);
}
