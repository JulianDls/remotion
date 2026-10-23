import {fitText} from '@remotion/layout-utils';
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {CFG, FPS, PAL, sec, syncArr, syncNum, W, wordTime} from '../config';
import {Glow, Streak} from '../components/Effects';
import {Particles} from '../components/Particles';
import {FONT_IMPACT, FONT_TEXT} from '../fonts';
import {clamp, easeOut} from '../lib/rng';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Posición y tamaño de cada palabra clave (fracciones del cuadro)
const KW_LAYOUT: Record<string, {x: number; y: number; size: number; align?: 'center' | 'left' | 'right'}> = {
	IDENTIDAD: {x: 0.5, y: 0.27, size: 140},
	PROPÓSITO: {x: 0.5, y: 0.4, size: 140},
	LLAMADOS: {x: 0.76, y: 0.56, size: 128},
	DESPIERTA: {x: 0.5, y: 0.5, size: 250},
	RESPONDE: {x: 0.5, y: 0.5, size: 250},
};

type KW = {word: string; start: number; end: number};

export const keywordTimeline = (): KW[] => {
	return CFG.palabrasClave
		.map((k) => {
			let start = k.inicio ?? null;
			if (start === null && k.vozId && k.enPalabra) {
				start = wordTime(k.vozId, k.enPalabra);
			}
			if (start === null) {
				return null;
			}
			const end = k.hasta ?? start + (k.duracion ?? 1.4);
			return {word: k.palabra, start, end};
		})
		.filter((x): x is KW => x !== null);
};

/** Palabras clave: aparecen en el instante exacto en que el narrador las pronuncia. */
export const Keywords: React.FC = () => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const items = keywordTimeline();
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			{items.map((k) => {
				if (t < k.start - 0.05 || t > k.end + 0.5) {
					return null;
				}
				const L = KW_LAYOUT[k.word] ?? {x: 0.5, y: 0.5, size: 180};
				const big = L.size >= 250;
				const inDur = big ? 0.18 : 0.35;
				const a = interpolate(t, [k.start, k.start + inDur, k.end, k.end + 0.45], [0, 1, 1, 0], CL);
				const grow = interpolate(t, [k.start, k.end + 0.45], [big ? 1.12 : 1.04, big ? 1.0 : 1.0], CL);
				const blur = interpolate(t, [k.start, k.start + inDur], [big ? 18 : 10, 0], CL) + interpolate(t, [k.end, k.end + 0.45], [0, 8], CL);
				const track = big ? interpolate(t, [k.start, k.end + 0.45], [0.3, 0.2], CL) : interpolate(t, [k.start, k.end + 0.45], [0.34, 0.22], CL);
				return (
					<React.Fragment key={k.word}>
					{big ? (
						<div
							style={{
								position: 'absolute',
								inset: 0,
								background: 'radial-gradient(ellipse 48% 24% at 50% 50%, rgba(5,6,10,0.55), transparent 100%)',
								opacity: a,
							}}
						/>
					) : null}
					<div
						style={{
							position: 'absolute',
							left: `${L.x * 100}%`,
							top: `${L.y * 100}%`,
							transform: `translate(-50%, -50%) scale(${grow})`,
							fontFamily: FONT_IMPACT,
							fontSize: L.size,
							letterSpacing: `${track}em`,
							paddingLeft: `${track}em`,
							color: PAL.blanco,
							opacity: a * (big ? 1 : 0.92),
							filter: `blur(${blur}px)`,
							whiteSpace: 'nowrap',
							lineHeight: 1,
							textShadow: big
								? `0 0 6px rgba(5,6,10,0.9), 0 0 28px rgba(5,6,10,0.75), 0 0 30px rgba(170,200,255,0.55), 0 0 90px rgba(79,140,255,0.5)`
								: `0 0 24px rgba(5,6,10,0.85), 0 0 50px rgba(233,184,106,0.35)`,
						}}
					>
						{k.word}
					</div>
					</React.Fragment>
				);
			})}
		</AbsoluteFill>
	);
};

/** Versículo bíblico en pantalla (Isaías 60:1, RVR1960). */
export const Verse: React.FC = () => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const v = CFG.evento.versiculo;
	const starts = syncArr('versiculoLineas');
	const tRef = syncNum('versiculoReferencia');
	const tOut = syncNum('versiculoSalida');
	if (t < starts[0] - 0.1 || t > tOut + 0.8) {
		return null;
	}
	const out = interpolate(t, [tOut, tOut + 0.6], [1, 0], CL);
	const lineStyle = (i: number): React.CSSProperties => {
		const s = starts[i] ?? starts[starts.length - 1];
		const p = clamp((t - s) / 0.9);
		const e = easeOut(p);
		return {
			opacity: e * out,
			transform: `translateY(${(1 - e) * 18}px)`,
			filter: `blur(${(1 - e) * 8}px)`,
			letterSpacing: `${0.16 + (1 - e) * 0.08}em`,
		};
	};
	const pr = easeOut(clamp((t - tRef) / 0.9));
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', pointerEvents: 'none'}}>
			<div style={{textAlign: 'center', marginTop: -10}}>
				{v.lineas.map((l, i) => (
					<div
						key={i}
						style={{
							fontFamily: FONT_TEXT,
							fontWeight: i < 2 ? 600 : 300,
							fontStyle: i < 2 ? 'normal' : 'italic',
							fontSize: i < 2 ? 70 : 44,
							textTransform: i < 2 ? 'uppercase' : 'none',
							color: PAL.blanco,
							lineHeight: i < 2 ? 1.18 : 1.6,
							marginTop: i === 2 ? 14 : 0,
							textShadow: '0 0 18px rgba(5,6,10,0.9), 0 0 42px rgba(5,6,10,0.7)',
							...lineStyle(i),
							...(i === 2 ? {letterSpacing: '0.04em'} : {}),
						}}
					>
						{l}
					</div>
				))}
				<div
					style={{
						marginTop: 30,
						fontFamily: FONT_TEXT,
						fontWeight: 500,
						fontSize: 26,
						letterSpacing: '0.42em',
						paddingLeft: '0.42em',
						color: PAL.dorado,
						opacity: pr * out,
						transform: `translateY(${(1 - pr) * 10}px)`,
						textShadow: '0 0 14px rgba(5,6,10,0.9)',
					}}
				>
					{v.referencia.toUpperCase()} · {v.traduccion}
				</div>
				<div style={{margin: '18px auto 0', height: 1, width: 360 * pr, background: `linear-gradient(90deg, transparent, ${PAL.dorado}, transparent)`, opacity: out}} />
			</div>
		</AbsoluteFill>
	);
};

/** Revelación del título: silencio, destello, título monumental, subtítulo y lema. */
export const Titulo: React.FC<{dur: number}> = () => {
	const frame = useCurrentFrame();
	const t0 = 75.0;
	const t = frame / FPS + t0;
	const tRev = syncNum('revelacionTitulo');
	const tSub = syncNum('subtitulo');
	const tFin = syncNum('impactoFinal');
	const name = CFG.evento.nombre;
	const fit = fitText({text: name, withinWidth: W * 0.84, fontFamily: FONT_IMPACT, letterSpacing: '0.06em'});
	const size = Math.min(290, fit.fontSize);
	const rev = clamp((t - tRev) / 0.9);
	const e = easeOut(rev);
	const sweep = interpolate(t, [tRev + 0.3, tRev + 2.6], [-0.4, 1.4], CL);
	const finalKick = t >= tFin ? Math.exp(-(t - tFin) * 3) : 0;
	const subA = easeOut(clamp((t - tSub) / 1.2));
	const lemaA = easeOut(clamp((t - tFin - 0.2) / 1.2));
	const push = 1.04 - 0.04 * clamp((t - tRev) / 14) + finalKick * 0.012;
	const hit = (at: number) => (t >= at ? Math.exp(-(t - at) * 9) : 0);
	const shk = (hit(tRev) * 12 + hit(tFin) * 9) * 1;
	const shx = Math.sin(frame * 2.3) * shk;
	const shy = Math.cos(frame * 1.9) * shk;
	const glowA = t < tRev ? 0 : 0.35 + 0.25 * Math.exp(-(t - tRev) * 1.2) + finalKick * 0.35;
	const endFade = CFG.video.finalSostenido ? 1 : interpolate(t, [89, 90], [1, 0], CL);
	return (
		<AbsoluteFill style={{background: PAL.negro, opacity: endFade}}>
			{/* resplandor de fondo y rayos */}
			<AbsoluteFill style={{opacity: t < tRev ? 0 : 1}}>
				<AbsoluteFill style={{background: `radial-gradient(ellipse 70% 55% at 50% 50%, rgba(79,140,255,${0.18 * e}) 0%, rgba(11,20,38,${0.7 * e}) 45%, transparent 80%)`}} />
				<AbsoluteFill
					style={{
						background: 'repeating-conic-gradient(from 0deg at 50% 50%, rgba(233,184,106,0.10) 0deg 2deg, transparent 2deg 11deg)',
						transform: `rotate(${(t - tRev) * 1.2}deg) scale(1.6)`,
						WebkitMaskImage: 'radial-gradient(circle at 50% 50%, black 0%, transparent 60%)',
						mixBlendMode: 'screen',
						opacity: 0.6 * e,
					}}
				/>
				<Glow x={0.5} y={0.5} r={760} color={PAL.dorado} opacity={glowA * 0.5} />
				<Streak x={0.5} y={0.47} width={0.9} opacity={0.18 * e + finalKick * 0.3} color="#ffd9a0" />
			</AbsoluteFill>
			<Particles
				count={260}
				seed={201}
				color="rgba(255,230,190,1)"
				size={[0.6, 2.4]}
				rise={[-2, -7]}
				drift={[-4, 4]}
				opacity={t < tRev ? 0.25 : 0.75}
				bokeh={0.12}
				offsetSec={0}
				burst={{x: 0.5, y: 0.5, atSec: tRev - t0, strength: 0.25}}
			/>
			{/* título */}
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
				<div style={{transform: `translate(${shx}px, ${shy}px) scale(${push})`, textAlign: 'center', marginTop: -40}}>
					<div
						style={{
							position: 'relative',
							fontFamily: FONT_IMPACT,
							fontSize: size,
							lineHeight: 1,
							letterSpacing: `${0.06 + (1 - e) * 0.25}em`,
							paddingLeft: `${0.06 + (1 - e) * 0.25}em`,
							opacity: e,
							filter: `blur(${(1 - e) * 14}px)`,
							whiteSpace: 'nowrap',
							backgroundImage: `linear-gradient(100deg, #e9d2a6 0%, #fff6e2 ${Math.max(0, sweep * 100 - 14)}%, #ffffff ${sweep * 100}%, #fff6e2 ${sweep * 100 + 14}%, #e9b86a 100%)`,
							WebkitBackgroundClip: 'text',
							color: 'transparent',
							textShadow: 'none',
						}}
					>
						{name}
					</div>
					<div
						style={{
							position: 'absolute',
							inset: 0,
							fontFamily: FONT_IMPACT,
							fontSize: size,
							lineHeight: 1,
							letterSpacing: `${0.06 + (1 - e) * 0.25}em`,
							paddingLeft: `${0.06 + (1 - e) * 0.25}em`,
							color: 'transparent',
							textShadow: `0 0 ${40 + finalKick * 40}px rgba(233,184,106,${0.55 * e}), 0 0 120px rgba(79,140,255,${0.35 * e})`,
							whiteSpace: 'nowrap',
							pointerEvents: 'none',
							zIndex: -1,
						}}
					>
						{name}
					</div>
					<div style={{margin: '34px auto 0', height: 2, width: `${60 * subA}%`, background: `linear-gradient(90deg, transparent, ${PAL.dorado}, transparent)`}} />
					<div
						style={{
							marginTop: 26,
							fontFamily: FONT_TEXT,
							fontWeight: 400,
							fontSize: 46,
							letterSpacing: `${0.3 + (1 - subA) * 0.2}em`,
							paddingLeft: '0.34em',
							textTransform: 'uppercase',
							color: PAL.blanco,
							opacity: subA,
							filter: `blur(${(1 - subA) * 6}px)`,
						}}
					>
						{CFG.evento.subtitulo}
					</div>
					<div
						style={{
							marginTop: 26,
							fontFamily: FONT_TEXT,
							fontStyle: 'italic',
							fontWeight: 500,
							fontSize: 40,
							letterSpacing: '0.06em',
							color: PAL.dorado,
							opacity: lemaA,
							transform: `translateY(${(1 - lemaA) * 12}px)`,
						}}
					>
						{CFG.evento.lema}
					</div>
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

void sec;
