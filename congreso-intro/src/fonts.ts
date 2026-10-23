import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const FONT_IMPACT = 'Bebas Neue';
export const FONT_TEXT = 'Montserrat';

loadFont({family: FONT_IMPACT, url: staticFile('fonts/BebasNeue-Regular.ttf'), weight: '400'});
loadFont({family: FONT_TEXT, url: staticFile('fonts/Montserrat-Variable.ttf'), weight: '100 900'});
loadFont({family: FONT_TEXT, url: staticFile('fonts/Montserrat-Italic-Variable.ttf'), weight: '100 900', style: 'italic'});
