import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FPS, FX, H, W} from '../config';
import {prep} from '../lib/canvas';
import {makeRng} from '../lib/rng';

type Props = {
	count: number;
	seed: number;
	color?: string;
	/** Tamaño en px (lejano, cercano). */
	size?: [number, number];
	/** Velocidad vertical en px/s (negativa = sube). */
	rise?: [number, number];
	drift?: [number, number];
	opacity?: number;
	/** Fracción de partículas cercanas desenfocadas (bokeh). */
	bokeh?: number;
	area?: {x0: number; y0: number; x1: number; y1: number};
	/** Instante (s) local de inicio para simulación determinista. */
	offsetSec?: number;
	twinkle?: number;
	/** Atracción hacia un punto (efecto de dispersión desde una luz). */
	burst?: {x: number; y: number; atSec: number; strength: number} | null;
	fadeIn?: number;
};

const makeSprite = (color: string, soft: number) => {
	const c = document.createElement('canvas');
	const s = 64;
	c.width = s;
	c.height = s;
	const g = c.getContext('2d')!;
	const grd = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
	grd.addColorStop(0, color);
	grd.addColorStop(soft, color);
	grd.addColorStop(1, 'rgba(0,0,0,0)');
	g.fillStyle = grd;
	g.fillRect(0, 0, s, s);
	return c;
};

/** Partículas de polvo / luz suspendidas, con profundidad y bokeh. */
export const Particles: React.FC<Props> = ({
	count,
	seed,
	color = 'rgba(255,236,200,1)',
	size = [0.8, 3.2],
	rise = [-6, -18],
	drift = [-6, 6],
	opacity = 0.8,
	bokeh = 0.12,
	area = {x0: 0, y0: 0, x1: 1, y1: 1},
	offsetSec = 0,
	twinkle = 0.5,
	burst = null,
	fadeIn = 0,
}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	const n = Math.round(count * FX.particulas * Math.min(1.5, FX.intensidadEfectos));
	const parts = useMemo(() => {
		const r = makeRng(seed);
		return Array.from({length: n}, () => {
			const z = r();
			const near = r() < bokeh;
			return {
				x: r(),
				y: r(),
				z,
				near,
				vy: rise[0] + (rise[1] - rise[0]) * z,
				vx: drift[0] + (drift[1] - drift[0]) * r(),
				ph: r() * Math.PI * 2,
				fq: 0.3 + r() * 1.2,
				amp: 4 + r() * 16,
				tw: r(),
			};
		});
	}, [n, seed, bokeh, rise, drift]);
	const sprites = useMemo(() => {
		if (typeof document === 'undefined') {
			return null;
		}
		return {sharp: makeSprite(color, 0.35), soft: makeSprite(color, 0.05)};
	}, [color]);

	useLayoutEffect(() => {
		const c = ref.current;
		if (!c || !sprites) {
			return;
		}
		const ctx = prep(c, W, H);
		ctx.globalCompositeOperation = 'lighter';
		const t = frame / FPS + offsetSec;
		const aw = (area.x1 - area.x0) * W;
		const ah = (area.y1 - area.y0) * H;
		const fade = fadeIn > 0 ? Math.min(1, frame / FPS / fadeIn) : 1;
		for (const p of parts) {
			let px = p.x * aw + p.vx * t + Math.sin(t * p.fq + p.ph) * p.amp;
			let py = p.y * ah + p.vy * t;
			if (burst && t > burst.atSec) {
				const dt = t - burst.atSec;
				const bx = (burst.x - area.x0) * W;
				const by = (burst.y - area.y0) * H;
				const dx = p.x * aw - bx;
				const dy = p.y * ah - by;
				const k = burst.strength * (1 - Math.exp(-dt * 1.5)) * (0.4 + p.z);
				px += dx * k;
				py += dy * k;
			}
			px = ((px % aw) + aw) % aw + area.x0 * W;
			py = ((py % ah) + ah) % ah + area.y0 * H;
			const sz = p.near ? size[1] * (4 + p.z * 6) : size[0] + (size[1] - size[0]) * p.z * p.z;
			const tw = 1 - twinkle + twinkle * (0.5 + 0.5 * Math.sin(t * (1.5 + p.tw * 3) + p.ph * 3));
			const a = (p.near ? 0.18 : 0.35 + 0.65 * p.z) * tw * opacity * fade;
			ctx.globalAlpha = Math.min(1, a);
			const img = p.near ? sprites.soft : sprites.sharp;
			const d = sz * (p.near ? 2.2 : 3.2);
			ctx.drawImage(img, px - d / 2, py - d / 2, d, d);
		}
		ctx.globalAlpha = 1;
		ctx.globalCompositeOperation = 'source-over';
	}, [frame, parts, sprites, area, size, opacity, offsetSec, twinkle, burst, fadeIn]);

	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<canvas ref={ref} style={{width: '100%', height: '100%'}} />
		</AbsoluteFill>
	);
};
