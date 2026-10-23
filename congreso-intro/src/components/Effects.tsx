import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {FPS, FX, H, PAL, W} from '../config';
import {prep} from '../lib/canvas';
import {clamp, makeRng} from '../lib/rng';

/** Niebla en mosaico que se desplaza (tintada mediante máscara CSS). */
export const Fog: React.FC<{
	tex?: 0 | 1;
	color?: string;
	opacity?: number;
	speed?: number;
	scale?: number;
	top?: number;
	bottom?: number;
	blend?: React.CSSProperties['mixBlendMode'];
	feather?: number;
}> = ({tex = 0, color = '#9fb0d0', opacity = 0.3, speed = 20, scale = 1, top = 0, bottom = 1, blend = 'screen', feather = 0.25}) => {
	const frame = useCurrentFrame();
	const tw = 2048 * scale;
	const th = 1024 * scale;
	const off = ((frame / FPS) * speed) % tw;
	const url = staticFile(`images/textures/niebla${tex}.webp`);
	const fade = `linear-gradient(to bottom, transparent 0%, black ${feather * 100}%, black ${(1 - feather) * 100}%, transparent 100%)`;
	return (
		<AbsoluteFill
			style={{
				top: `${top * 100}%`,
				height: `${(bottom - top) * 100}%`,
				opacity: opacity * FX.niebla * Math.min(1.5, FX.intensidadEfectos),
				mixBlendMode: blend,
				WebkitMaskImage: fade,
				pointerEvents: 'none',
			}}
		>
			<AbsoluteFill
				style={{
					backgroundColor: color,
					WebkitMaskImage: `url(${url})`,
					WebkitMaskSize: `${tw}px ${th}px`,
					WebkitMaskRepeat: 'repeat',
					WebkitMaskPosition: `${-off}px ${(frame / FPS) * speed * 0.08}px`,
				}}
			/>
		</AbsoluteFill>
	);
};

/** Grano de película generado por fotograma (determinista). */
export const Grain: React.FC<{amount?: number}> = ({amount = 0.07}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		const pr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
		const w = Math.round(960 * pr);
		const h = Math.round(540 * pr);
		if (c.width !== w) {
			c.width = w;
			c.height = h;
		}
		const ctx = c.getContext('2d')!;
		const img = ctx.createImageData(w, h);
		const r = makeRng(frame * 7919 + 1);
		const d = img.data;
		for (let i = 0; i < d.length; i += 4) {
			const v = 128 + (r() + r() + r() - 1.5) * 95;
			d[i] = v;
			d[i + 1] = v;
			d[i + 2] = v;
			d[i + 3] = 255;
		}
		ctx.putImageData(img, 0, 0);
	}, [frame]);
	const a = amount * FX.grano * Math.min(1.5, FX.intensidadEfectos);
	if (a <= 0) {
		return null;
	}
	return (
		<AbsoluteFill style={{mixBlendMode: 'overlay', opacity: a, pointerEvents: 'none'}}>
			<canvas ref={ref} style={{width: '100%', height: '100%', imageRendering: 'auto'}} />
		</AbsoluteFill>
	);
};

export const Vignette: React.FC<{strength?: number; color?: string}> = ({strength = 0.65, color = PAL.negro}) => (
	<AbsoluteFill
		style={{
			background: `radial-gradient(ellipse 75% 70% at 50% 50%, transparent 45%, ${color} 140%)`,
			opacity: strength,
			pointerEvents: 'none',
		}}
	/>
);

/** Franjas de cine 2.39:1; open (0..1) las retira. */
export const Letterbox: React.FC<{open: number}> = ({open}) => {
	const bar = ((H - W / 2.39) / 2) * (1 - clamp(open));
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: '#000'}} />
			<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: '#000'}} />
		</AbsoluteFill>
	);
};

/** Destello (blanco o dorado) breve. */
export const Flash: React.FC<{at: number; dur?: number; peak?: number; color?: string; attack?: number}> = ({at, dur = 8, peak = 0.9, color = PAL.blanco, attack = 1}) => {
	const frame = useCurrentFrame();
	const k = FX.destellos;
	if (frame < at - attack || frame > at + dur) {
		return null;
	}
	const o = interpolate(frame, [at - attack, at, at + dur], [0, peak, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return <AbsoluteFill style={{background: color, opacity: o * k, mixBlendMode: 'screen', pointerEvents: 'none'}} />;
};

/** Halo de luz suave (para fuentes de luz y destellos de lente). */
export const Glow: React.FC<{x: number; y: number; r: number; color?: string; opacity?: number; blend?: React.CSSProperties['mixBlendMode']}> = ({
	x,
	y,
	r,
	color = PAL.dorado,
	opacity = 0.6,
	blend = 'screen',
}) => (
	<AbsoluteFill
		style={{
			background: `radial-gradient(circle ${r}px at ${x * 100}% ${y * 100}%, ${color} 0%, transparent 100%)`,
			opacity,
			mixBlendMode: blend,
			pointerEvents: 'none',
		}}
	/>
);

/** Destello anamórfico horizontal. */
export const Streak: React.FC<{x: number; y: number; width?: number; opacity?: number; color?: string}> = ({x, y, width = 1.4, opacity = 0.5, color = '#9cc0ff'}) => (
	<AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity}}>
		<div
			style={{
				position: 'absolute',
				left: `${(x - width / 2) * 100}%`,
				width: `${width * 100}%`,
				top: `calc(${y * 100}% - 3px)`,
				height: 6,
				background: `radial-gradient(ellipse 50% 50% at 50% 50%, ${color} 0%, transparent 100%)`,
				filter: 'blur(1.5px)',
			}}
		/>
	</AbsoluteFill>
);

void prep;
