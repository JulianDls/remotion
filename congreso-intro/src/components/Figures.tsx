import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FPS, H, W} from '../config';
import {dpr, prep} from '../lib/canvas';
import {DrawOpts, drawLitFigure, Pose, randomStyle, Style, View} from '../lib/figure';

export type FigureSpec = {
	x: number; // normalizado (pies)
	y: number;
	h: number; // altura normalizada respecto al alto del cuadro
	view: View;
	facing?: 1 | -1;
	pose: (t: number) => Pose;
	styleSeed: number;
	style?: Partial<Style>;
	fill?: string;
	rim?: string;
	rimDir?: [number, number];
	/** Desplazamiento a lo largo del tiempo (normalizado por segundo). */
	vx?: number;
	vy?: number;
	/** Crecimiento de escala por segundo (figura que se acerca). */
	grow?: number;
	opacity?: number;
	/** Perfil del suelo (y normalizada muestreada en x de 0 a 1): la figura lo sigue al desplazarse. */
	ground?: number[];
	groundOffset?: number;
};

/**
 * Dibuja siluetas sobre un canvas a resolución de render, con halo de contraluz opcional.
 */
export const Figures: React.FC<{
	figures: FigureSpec[];
	glow?: {color: string; blur: number; opacity: number} | null;
	fill?: string;
	offsetSec?: number;
}> = ({figures, glow = null, fill = '#05070c', offsetSec = 0}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	const glowBufs = useRef<HTMLCanvasElement[] | null>(null);
	const styles = useMemo(() => figures.map((f) => ({...randomStyle(f.styleSeed), ...(f.style ?? {})})), [figures]);
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		const ctx = prep(c, W, H);
		const t = frame / FPS + offsetSec;
		const opts: (DrawOpts & {rim?: string; rimDir?: [number, number]; opacity: number})[] = figures.map((f, i) => {
			const g = 1 + (f.grow ?? 0) * t;
			const nx = f.x + (f.vx ?? 0) * t;
			let ny = f.y + (f.vy ?? 0) * t;
			if (f.ground && f.ground.length > 1) {
				const gp = Math.min(f.ground.length - 1.001, Math.max(0, nx * (f.ground.length - 1)));
				const i0 = Math.floor(gp);
				const fr = gp - i0;
				ny = f.ground[i0] * (1 - fr) + f.ground[i0 + 1] * fr + (f.groundOffset ?? 0.004);
			}
			return {
				x: nx * W,
				y: ny * H,
				h: f.h * H * g,
				view: f.view,
				facing: f.facing,
				pose: f.pose(t),
				style: styles[i],
				fill: f.fill ?? fill,
				rim: f.rim,
				rimDir: f.rimDir,
				opacity: f.opacity ?? 1,
			};
		});
		// orden: de lejos (más pequeñas / más arriba) a cerca
		const order = opts.map((o, i) => ({o, i})).sort((a, b) => a.o.y - b.o.y);
		if (glow && glow.opacity > 0) {
			// halo calculado a 1/4 de resolución (un desenfoque grande no necesita detalle)
			const r = dpr();
			const ds = 4;
			const lw = Math.ceil(c.width / ds);
			const lh = Math.ceil(c.height / ds);
			const mk = () => {
				const cv = document.createElement('canvas');
				cv.width = lw;
				cv.height = lh;
				return cv;
			};
			if (!glowBufs.current || glowBufs.current[0].width !== lw) {
				glowBufs.current = [mk(), mk()];
			}
			const [m0, m1] = glowBufs.current;
			const g0 = m0.getContext('2d')!;
			g0.setTransform(1, 0, 0, 1, 0, 0);
			g0.clearRect(0, 0, lw, lh);
			g0.setTransform(r / ds, 0, 0, r / ds, 0, 0);
			for (const {o} of order) {
				drawLitFigure(g0, {...o, fill: glow.color, rim: undefined});
			}
			const g1 = m1.getContext('2d')!;
			g1.setTransform(1, 0, 0, 1, 0, 0);
			g1.clearRect(0, 0, lw, lh);
			g1.filter = `blur(${(glow.blur * r) / ds}px)`;
			g1.drawImage(m0, 0, 0);
			g1.globalAlpha = 0.6;
			g1.filter = `blur(${(glow.blur * r * 3) / ds}px)`;
			g1.drawImage(m0, 0, 0);
			g1.globalAlpha = 1;
			g1.filter = 'none';
			ctx.save();
			ctx.setTransform(1, 0, 0, 1, 0, 0);
			ctx.globalCompositeOperation = 'lighter';
			ctx.globalAlpha = glow.opacity;
			ctx.imageSmoothingQuality = 'high';
			ctx.drawImage(m1, 0, 0, c.width, c.height);
			ctx.restore();
		}
		for (const {o} of order) {
			ctx.globalAlpha = o.opacity;
			drawLitFigure(ctx, o);
		}
		ctx.globalAlpha = 1;
	}, [frame, figures, styles, glow, fill, offsetSec]);
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<canvas ref={ref} style={{width: '100%', height: '100%'}} />
		</AbsoluteFill>
	);
};
