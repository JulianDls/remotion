import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {CFG, FPS, PAL, Plano, sec, syncArr, syncNum} from './config';
import {Flash, Grain, Letterbox, Vignette} from './components/Effects';
import './fonts';
import {
	Acantilado,
	Amanecer,
	Azotea,
	Calle,
	Caminantes,
	Cielo,
	CiudadAerea,
	Cumbre,
	Horizonte,
	Nubes,
	Rayos,
	SceneProps,
	Tormenta,
	Transicion,
	VoidDust,
} from './scenes/Landscapes';
import {Adoracion, Auditorio, Mano, Montaje, montageCuts, Multitud, PalabraFondo, Perfil, Puerta} from './scenes/People';
import {Keywords, Titulo, Verse} from './scenes/Text';

const SCENES: Record<string, React.FC<SceneProps>> = {
	vacio: VoidDust,
	horizonte: Horizonte,
	ciudad: CiudadAerea,
	calle: Calle,
	azotea: Azotea,
	acantilado: Acantilado,
	tormenta: Tormenta,
	perfil: Perfil,
	cumbre: Cumbre,
	caminantes: Caminantes,
	rayos: Rayos,
	nubes: Nubes,
	transicion: Transicion,
	cielo: Cielo,
	puerta: Puerta,
	multitud: Multitud,
	adoracion: Adoracion,
	mano: Mano,
	auditorio: Auditorio,
	palabra: PalabraFondo,
	amanecer: Amanecer,
	montaje: Montaje,
	titulo: ({dur}) => <Titulo dur={dur} />,
};

/** Fundidos de entrada (en fotogramas) para los planos que no entran por corte seco. */
const FADE_IN: Record<string, number> = {'1A': 24, '1B': 36};

const Shot: React.FC<{plano: Plano}> = ({plano}) => {
	const frame = useCurrentFrame();
	const C = SCENES[plano.tipo];
	const fade = FADE_IN[plano.id] ?? 0;
	const dur = sec(plano.fin) - sec(plano.inicio) + fade;
	const o = fade > 0 ? interpolate(frame, [0, fade], [0, 1], {extrapolateRight: 'clamp'}) : 1;
	if (!C) {
		return null;
	}
	return (
		<AbsoluteFill style={{opacity: o}}>
			<C plano={plano} dur={dur} />
		</AbsoluteFill>
	);
};

/** Destellos en cada corte del montaje final (73-75 s), sincronizados con estilo.velocidadEdicion. */
const montageFlashes = () => {
	const plano = CFG.planos.find((p) => p.tipo === 'montaje');
	if (!plano) {
		return [];
	}
	const n = montageCuts();
	const len = plano.fin - plano.inicio;
	return Array.from({length: n - 1}, (_, k) => ({at: plano.inicio + ((k + 1) * len) / n, peak: k === n - 2 ? 0.4 : 0.24, dur: 4}));
};

export const Intro: React.FC = () => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const tRev = syncNum('revelacionTitulo');
	const open = CFG.video.franjasCine ? interpolate(t, [tRev, tRev + 1.2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
	const flashes: {at: number; peak: number; dur: number; color?: string}[] = [
		{at: syncNum('transicionPalabra'), peak: 0.85, dur: 14},
		...syncArr('golpesDeclaracion').map((a) => ({at: a, peak: 0.55, dur: 9})),
		{at: syncNum('inicioGroove'), peak: 0.7, dur: 10},
		{at: 68.0, peak: 0.4, dur: 7},
		...montageFlashes(),
		{at: tRev, peak: 1.0, dur: 22, color: '#fff3dd'},
		{at: syncNum('impactoFinal'), peak: 0.45, dur: 16, color: PAL.dorado},
	];
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			{CFG.planos.map((p) => {
				const fade = FADE_IN[p.id] ?? 0;
				const from = sec(p.inicio) - fade;
				return (
					<Sequence key={p.id} from={Math.max(0, from)} durationInFrames={sec(p.fin) - sec(p.inicio) + fade} premountFor={45} name={`${p.id} ${p.tipo}`}>
						<Shot plano={p} />
					</Sequence>
				);
			})}
			<Keywords />
			<Verse />
			{flashes.map((f, i) => (
				<Flash key={i} at={sec(f.at)} peak={f.peak} dur={f.dur} color={f.color} />
			))}
			<Vignette strength={t < tRev ? 0.7 : 0.45} />
			<Grain amount={0.08} />
			<Letterbox open={open} />
			<Audio src={staticFile('audio/mix.wav')} />
		</AbsoluteFill>
	);
};
