import React, {createContext, useContext} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FX, H, W} from '../config';
import {clamp, easeInOut, noise1} from '../lib/rng';

export type CamMove = {
	/** Escala a profundidad 1 al inicio y al final del plano. */
	zoom?: [number, number];
	/** Desplazamiento de cámara en fracción del ancho/alto (contenido se mueve al revés). */
	x?: [number, number];
	y?: [number, number];
	/** Giro (grados) de toda la imagen. */
	roll?: [number, number];
	ease?: (t: number) => number;
	/** Vibración (px) — p. ej. tras un impacto. */
	shake?: number;
	shakeDecay?: number;
};

type CamState = {zoom: number; x: number; y: number; frame: number};
const Ctx = createContext<CamState>({zoom: 1, x: 0, y: 0, frame: 0});

export const useCam = () => useContext(Ctx);

export const Camera: React.FC<{move: CamMove; durationInFrames: number; children: React.ReactNode}> = ({move, durationInFrames, children}) => {
	const frame = useCurrentFrame();
	const e = move.ease ?? easeInOut;
	const speed = FX.velocidadCamara;
	const tRaw = clamp(frame / Math.max(1, durationInFrames - 1));
	const t = e(tRaw);
	const lerp2 = (v: [number, number] | undefined, d: number) => (v ? v[0] + (v[1] - v[0]) * t * speed : d);
	const zoom = move.zoom ? move.zoom[0] + (move.zoom[1] - move.zoom[0]) * t * speed : 1;
	const x = lerp2(move.x, 0);
	const y = lerp2(move.y, 0);
	const roll = move.roll ? move.roll[0] + (move.roll[1] - move.roll[0]) * t : 0;
	let sx = 0;
	let sy = 0;
	if (move.shake) {
		const decay = Math.exp(-frame / (move.shakeDecay ?? 8));
		sx = noise1(frame * 0.9, 1) * move.shake * decay;
		sy = noise1(frame * 0.9, 2) * move.shake * decay;
	}
	return (
		<Ctx.Provider value={{zoom, x, y, frame}}>
			<AbsoluteFill style={{transform: `translate(${sx}px, ${sy}px) rotate(${roll}deg)`, overflow: 'hidden'}}>{children}</AbsoluteFill>
		</Ctx.Provider>
	);
};

/** Capa con parallax: depth 0 = infinito (quieta), 1 = plano focal, >1 = primer plano. */
export const Layer: React.FC<{
	depth: number;
	children: React.ReactNode;
	style?: React.CSSProperties;
	baseScale?: number;
	origin?: [number, number];
	blend?: React.CSSProperties['mixBlendMode'];
	opacity?: number;
}> = ({depth, children, style, baseScale = 1.06, origin = [0.5, 0.5], blend, opacity}) => {
	const cam = useCam();
	const s = baseScale * (1 + (cam.zoom - 1) * depth);
	const tx = -cam.x * depth * W;
	const ty = -cam.y * depth * H;
	return (
		<AbsoluteFill
			style={{
				transform: `translate(${tx}px, ${ty}px) scale(${s})`,
				transformOrigin: `${origin[0] * 100}% ${origin[1] * 100}%`,
				mixBlendMode: blend,
				opacity,
				...style,
			}}
		>
			{children}
		</AbsoluteFill>
	);
};
