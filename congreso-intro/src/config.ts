import raw from '../config/intro.config.json';
import manifestRaw from '../public/audio/voice/manifest.json';
import platesRaw from '../public/images/plates/meta.json';

export type Narracion = {
	id: string;
	escena: number;
	inicio: number;
	registro: string;
	texto: string;
};

export type PalabraClave = {
	palabra: string;
	vozId?: string;
	enPalabra?: string;
	inicio?: number;
	duracion?: number;
	hasta?: number;
};

export type Plano = {
	id: string;
	tipo: string;
	inicio: number;
	fin: number;
	descripcion: string;
};

export type IntroConfig = {
	evento: {
		nombre: string;
		subtitulo: string;
		lema: string;
		versiculo: {lineas: string[]; referencia: string; traduccion: string};
	};
	video: {fps: number; ancho: number; alto: number; duracionSegundos: number; franjasCine: boolean; finalSostenido: boolean};
	paleta: {negro: string; azulNoche: string; azulElectrico: string; blanco: string; dorado: string};
	tipografia: {impacto: string; secundaria: string};
	estilo: {
		intensidadEfectos: number;
		particulas: number;
		niebla: number;
		grano: number;
		destellos: number;
		velocidadCamara: number;
		velocidadEdicion: number;
	};
	audio: {volumenVoz: number; volumenMusica: number; volumenEfectos: number};
	narracion: Narracion[];
	palabrasClave: PalabraClave[];
	escenas: {n: number; nombre: string; inicio: number; fin: number}[];
	sincronia: Record<string, number | number[] | string>;
	planos: Plano[];
};

export type VoiceLine = {
	id: string;
	duracion: number;
	palabras: {w: string; start: number; end: number}[];
};

export type PlateMeta = {
	capas?: string[];
	luz?: [number, number];
	rayos?: string;
	[k: string]: unknown;
};

export const CFG = raw as unknown as IntroConfig;
export const VOICE = (manifestRaw as unknown as {lines: VoiceLine[]}).lines;
export const PLATES = platesRaw as unknown as Record<string, PlateMeta>;

export const FPS = CFG.video.fps;
export const W = CFG.video.ancho;
export const H = CFG.video.alto;
export const TOTAL_FRAMES = Math.round(CFG.video.duracionSegundos * FPS);
export const PAL = CFG.paleta;
export const FX = CFG.estilo;

export const sec = (s: number) => Math.round(s * FPS);

export const syncNum = (k: string): number => CFG.sincronia[k] as number;
export const syncArr = (k: string): number[] => CFG.sincronia[k] as number[];

/** Instante (s) en el que el narrador pronuncia una palabra de una línea. */
export const wordTime = (vozId: string, word: string): number | null => {
	const line = CFG.narracion.find((l) => l.id === vozId);
	const v = VOICE.find((l) => l.id === vozId);
	if (!line || !v) {
		return null;
	}
	const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
	const w = v.palabras.find((p) => norm(p.w) === norm(word));
	return w ? line.inicio + w.start : null;
};
