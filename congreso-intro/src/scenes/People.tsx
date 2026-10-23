import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill, Img, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {FPS, H, PAL, PLATES, W} from '../config';
import {Camera, Layer} from '../components/Camera';
import {Fog, Glow, Streak} from '../components/Effects';
import {Figures, FigureSpec} from '../components/Figures';
import {Particles} from '../components/Particles';
import {PlateScene, plateUrl} from '../components/PlateScene';
import {prep} from '../lib/canvas';
import {drawHand, drawProfile} from '../lib/closeups';
import {basePose, walkPose, worshipPose} from '../lib/figure';
import {clamp, easeIn, easeInOut, easeOut, makeRng} from '../lib/rng';
import {Amanecer, SceneProps} from './Landscapes';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// ------------------------------------------------------------------ haces de luz de escenario
type Beam = {x: number; y: number; angle: number; sweep: number; speed: number; phase: number; width: number; len: number; color: string; alpha: number};

const Beams: React.FC<{beams: Beam[]; intensity?: number}> = ({beams, intensity = 1}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		// los haces son difusos: se dibujan a un tercio de resolución y el navegador los escala
		const LW = Math.round(W / 3);
		const LH = Math.round(H / 3);
		if (c.width !== LW) {
			c.width = LW;
			c.height = LH;
		}
		const ctx = c.getContext('2d')!;
		ctx.setTransform(1 / 3, 0, 0, 1 / 3, 0, 0);
		ctx.clearRect(0, 0, W, H);
		ctx.globalCompositeOperation = 'lighter';
		const t = frame / FPS;
		for (const b of beams) {
			const a = b.angle + Math.sin(t * b.speed + b.phase) * b.sweep;
			const sx = b.x * W;
			const sy = b.y * H;
			const len = b.len * H;
			const ex = sx + Math.sin(a) * len;
			const ey = sy + Math.cos(a) * len;
			const nx = Math.cos(a);
			const ny = -Math.sin(a);
			const hw = b.width * H;
			const g = ctx.createLinearGradient(sx, sy, ex, ey);
			g.addColorStop(0, b.color);
			g.addColorStop(1, 'rgba(0,0,0,0)');
			ctx.globalAlpha = b.alpha * intensity;
			ctx.fillStyle = g;
			ctx.beginPath();
			ctx.moveTo(sx - nx * hw * 0.04, sy - ny * hw * 0.04);
			ctx.lineTo(sx + nx * hw * 0.04, sy + ny * hw * 0.04);
			ctx.lineTo(ex + nx * hw, ey + ny * hw);
			ctx.lineTo(ex - nx * hw, ey - ny * hw);
			ctx.closePath();
			ctx.fill();
			// núcleo más brillante
			ctx.globalAlpha = b.alpha * intensity * 0.6;
			ctx.beginPath();
			ctx.moveTo(sx, sy);
			ctx.lineTo(ex + nx * hw * 0.25, ey + ny * hw * 0.25);
			ctx.lineTo(ex - nx * hw * 0.25, ey - ny * hw * 0.25);
			ctx.closePath();
			ctx.fill();
			// fuente
			const rg = ctx.createRadialGradient(sx, sy, 0, sx, sy, H * 0.05);
			rg.addColorStop(0, 'rgba(255,255,255,1)');
			rg.addColorStop(1, 'rgba(255,255,255,0)');
			ctx.globalAlpha = intensity;
			ctx.fillStyle = rg;
			ctx.fillRect(sx - H * 0.05, sy - H * 0.05, H * 0.1, H * 0.1);
		}
		ctx.globalAlpha = 1;
	}, [frame, beams, intensity]);
	return (
		<AbsoluteFill style={{mixBlendMode: 'screen', pointerEvents: 'none'}}>
			<canvas ref={ref} style={{width: '100%', height: '100%'}} />
		</AbsoluteFill>
	);
};

const makeBeams = (seed: number, n: number, colors: string[], sweep: number, speed: number): Beam[] => {
	const r = makeRng(seed);
	return Array.from({length: n}, (_, i) => ({
		x: 0.08 + (i / Math.max(1, n - 1)) * 0.84,
		y: 0.02 + r() * 0.04,
		angle: (0.5 - i / Math.max(1, n - 1)) * 0.7 + (r() - 0.5) * 0.2,
		sweep: sweep * (0.6 + r() * 0.8),
		speed: speed * (0.7 + r() * 0.6),
		phase: r() * 6.28,
		width: 0.12 + r() * 0.08,
		len: 1.25,
		color: colors[i % colors.length],
		alpha: 0.18 + r() * 0.12,
	}));
};

// ------------------------------------------------------------------ 3B / 3I: perfil levantando la mirada
export const Perfil: React.FC<SceneProps> = ({plano, dur}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	const quick = plano.id === '3I';
	const p = clamp(frame / Math.max(1, dur - 1));
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		const ctx = prep(c, W, H);
		const tilt = quick ? 0.26 + 0.08 * p : 0.02 + 0.26 * easeInOut(p);
		const s = (quick ? 0.56 : 0.42) * H * (1 + p * 0.03);
		const x = (quick ? 0.4 : 0.43) * W;
		const y = (quick ? 0.5 : 0.47) * H;
		// halo de luz que desborda el contorno
		ctx.save();
		ctx.filter = `blur(${H * 0.012}px)`;
		ctx.globalAlpha = 0.55;
		drawProfile(ctx, {x: x + 4, y: y - 3, scale: s, tilt, fill: 'rgba(255,214,150,1)', rim: 'rgba(255,214,150,1)', rimPx: 0, t: frame / FPS});
		ctx.restore();
		drawProfile(ctx, {x, y, scale: s, tilt, fill: '#04050a', rim: 'rgba(255,226,180,1)', rimPx: Math.max(2, s * 0.008), t: frame / FPS});
	}, [frame, p, quick]);
	const lightX = quick ? 0.82 : 0.86;
	return (
		<AbsoluteFill style={{background: `radial-gradient(ellipse 80% 90% at ${lightX * 100}% 22%, #fff4dc 0%, #e9b86a 18%, #5a4a52 45%, #0b1426 75%, #05060a 100%)`}}>
			<Camera move={{zoom: [1.0, 1.05], x: [0, 0.01]}} durationInFrames={dur}>
				<Layer depth={0.3}>
					<Glow x={lightX} y={0.2} r={420} color="#ffffff" opacity={0.55} />
				</Layer>
				<Layer depth={0.6}>
					<Particles count={120} seed={121} color="rgba(255,235,200,1)" size={[0.8, 3]} rise={[-4, -12]} drift={[-6, 2]} opacity={0.7} bokeh={0.35} />
				</Layer>
				<Layer depth={1.0}>
					<AbsoluteFill>
						<canvas ref={ref} style={{width: '100%', height: '100%'}} />
					</AbsoluteFill>
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 4B: la puerta monumental se abre
export const Puerta: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const m = PLATES.puerta ?? {};
	const pr = (m.puerta as number[] | undefined) ?? [0.425, 0.2, 0.15, 0.5];
	const t = frame / FPS;
	const open = 0.06 + 0.94 * easeInOut(clamp((t - 0.3) / 2.6));
	const leafScale = 1 - open * 0.86;
	const figs: FigureSpec[] = useMemo(
		() =>
			[0.44, 0.5, 0.555, 0.47].map((x, i) => ({
				x,
				y: 0.9 + (i === 3 ? 0.06 : 0),
				h: i === 3 ? 0.3 : 0.24 + (i % 2) * 0.02,
				view: 'front' as const,
				pose: (tt: number) => (tt < 0.9 ? basePose() : walkPose((tt - 0.9) * 4.6 + i * 1.3, 0.7)),
				styleSeed: 140 + i,
				rim: 'rgba(255,230,190,1)',
				rimDir: [0, -1] as [number, number],
				vy: -0.012,
				grow: -0.04,
			})),
		[],
	);
	const leaf = (side: 'izq' | 'der') => {
		const left = side === 'izq';
		return (
			<div
				style={{
					position: 'absolute',
					left: `${(pr[0] + (left ? 0 : pr[2] / 2)) * 100}%`,
					top: `${pr[1] * 100}%`,
					width: `${(pr[2] / 2) * 100}%`,
					height: `${pr[3] * 100}%`,
					transformOrigin: left ? '0% 50%' : '100% 50%',
					transform: `perspective(1400px) rotateY(${(left ? -1 : 1) * open * 78}deg) scaleX(${0.98 + leafScale * 0.02})`,
				}}
			>
				<Img src={plateUrl('puerta', `hoja_${side}.webp`)} style={{width: '100%', height: '100%'}} />
			</div>
		);
	};
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.09]}} durationInFrames={dur}>
				<Layer depth={0.5}>
					<Img src={plateUrl('puerta', 'luz.jpg')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</Layer>
				<Layer depth={0.5} blend="screen" opacity={open}>
					<Img src={plateUrl('puerta', 'rayos.webp')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</Layer>
				<Layer depth={0.5}>
					<Img src={plateUrl('puerta', 'muro.webp')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
					{leaf('izq')}
					{leaf('der')}
				</Layer>
				<Layer depth={0.5} blend="screen" opacity={open * 0.95}>
					<Img src={plateUrl('puerta', 'derrame.webp')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</Layer>
				<Layer depth={0.5} style={{WebkitMaskImage: `radial-gradient(ellipse 30% 60% at 50% 55%, black, transparent)`}}>
					<Particles count={160} seed={141} color="rgba(255,235,200,1)" size={[0.6, 2.2]} rise={[-3, -8]} drift={[-3, 3]} opacity={0.9 * open} bokeh={0.1} />
				</Layer>
				<Layer depth={0.7}>
					<Figures figures={figs} glow={{color: 'rgba(255,225,180,1)', blur: 8, opacity: 0.6 * open}} />
				</Layer>
				<Layer depth={0.5}>
					<Glow x={pr[0] + pr[2] / 2} y={pr[1] + pr[3] * 0.55} r={520} color="#ffe6c0" opacity={0.22 + 0.25 * open} />
				</Layer>
				<Layer depth={1.2}>
					<Img src={plateUrl('puerta', 'columnas.webp')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ multitud (de espaldas) frente a la luz
const crowd = (seed: number, rows: {n: number; y: number; h: number; x0: number; x1: number; jitter: number}[], pose: (t: number, i: number) => ReturnType<typeof basePose>, rim: string) => {
	const r = makeRng(seed);
	const out: FigureSpec[] = [];
	let k = 0;
	for (const row of rows) {
		for (let i = 0; i < row.n; i++) {
			const idx = k++;
			out.push({
				x: row.x0 + ((i + 0.5) / row.n) * (row.x1 - row.x0) + (r() - 0.5) * row.jitter,
				y: row.y + (r() - 0.5) * row.h * 0.06,
				h: row.h * (0.9 + r() * 0.18),
				view: 'front',
				pose: (t: number) => pose(t, idx),
				styleSeed: seed * 100 + idx,
				rim,
				rimDir: [0, -1],
			});
		}
	}
	return out;
};

export const Multitud: React.FC<SceneProps> = ({dur}) => {
	const figs = useMemo(
		() =>
			crowd(
				15,
				[
					{n: 22, y: 0.74, h: 0.17, x0: -0.02, x1: 1.02, jitter: 0.03},
					{n: 14, y: 0.86, h: 0.27, x0: -0.03, x1: 1.03, jitter: 0.04},
					{n: 8, y: 1.08, h: 0.48, x0: -0.05, x1: 1.05, jitter: 0.05},
				],
				(t, i) => ({...basePose(), head: 0.1 + 0.05 * Math.sin(t * 0.5 + i), sway: 0.004 * Math.sin(t * 0.8 + i * 1.7)}),
				'rgba(255,220,170,1)',
			),
		[],
	);
	const m = PLATES.amanecer ?? {};
	const luz = (m.luz as [number, number] | undefined) ?? [0.5, 0.48];
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.03, 1.09], y: [0.04, -0.01]}} durationInFrames={dur}>
				<PlateScene env="amanecer" depths={[0.6, 0.35, 0.2]} />
				<Layer depth={0.25}>
					<Glow x={luz[0]} y={luz[1]} r={600} color="#ffe2b0" opacity={0.35} />
				</Layer>
				<Layer depth={1.0}>
					<Figures figures={figs} glow={{color: 'rgba(255,205,140,1)', blur: 6, opacity: 0.5}} />
				</Layer>
				<Layer depth={1.1}>
					<Particles count={100} seed={151} color="rgba(255,225,180,1)" size={[0.6, 2.2]} rise={[-3, -8]} drift={[-4, 4]} opacity={0.5} bokeh={0.15} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5A / 5G / 5J: adoración con haces de luz
export const Adoracion: React.FC<SceneProps & {sub?: string}> = ({plano, dur, sub}) => {
	const v = sub ?? plano.id;
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const beams = useMemo(
		() => makeBeams(v === '5G' ? 33 : 31, 7, ['rgba(255,240,215,1)', 'rgba(140,175,255,1)', 'rgba(233,184,106,1)'], v === '5G' ? 0.45 : 0.16, v === '5G' ? 2.4 : 0.8),
		[v],
	);
	const figs = useMemo(
		() =>
			crowd(
				v === '5J' ? 27 : 25,
				v === '5J'
					? [
							{n: 12, y: 0.82, h: 0.32, x0: -0.03, x1: 1.03, jitter: 0.04},
							{n: 6, y: 1.12, h: 0.62, x0: -0.06, x1: 1.06, jitter: 0.05},
						]
					: [
							{n: 26, y: 0.7, h: 0.17, x0: -0.02, x1: 1.02, jitter: 0.025},
							{n: 16, y: 0.84, h: 0.3, x0: -0.03, x1: 1.03, jitter: 0.04},
							{n: 8, y: 1.1, h: 0.56, x0: -0.05, x1: 1.05, jitter: 0.05},
						],
				(tt, i) => worshipPose(tt + 57, i, 1),
				'rgba(210,225,255,1)',
			),
		[v],
	);
	const pulse = v === '5A' ? interpolate(t, [0, 0.25, 1.9], [1.4, 1.0, 0.9], CL) : 1;
	return (
		<AbsoluteFill style={{background: 'radial-gradient(ellipse 90% 70% at 50% 30%, #1b2a4a 0%, #0b1426 45%, #05060a 85%)'}}>
			<Camera move={v === '5J' ? {zoom: [1.06, 1.12]} : {zoom: [1.0, 1.06], y: [0.01, -0.01], shake: v === '5A' ? 9 : 0, shakeDecay: 7}} durationInFrames={dur}>
				<Layer depth={0.3}>
					<Glow x={0.5} y={0.38} r={700} color="#cfdcff" opacity={0.55 * pulse} />
					<Glow x={0.5} y={0.42} r={260} color="#ffffff" opacity={0.65 * pulse} />
					<Streak x={0.5} y={0.42} width={1.5} opacity={0.6} color="#9cc0ff" />
				</Layer>
				<Layer depth={0.4}>
					<Beams beams={beams} intensity={pulse} />
				</Layer>
				<Layer depth={0.5}>
					<Fog tex={0} color="#9fb4e8" opacity={0.28} speed={25} top={0.15} bottom={0.8} />
				</Layer>
				<Layer depth={1.0}>
					<Figures figures={figs} glow={{color: 'rgba(200,220,255,1)', blur: 7, opacity: 0.55}} />
				</Layer>
				<Layer depth={1.1}>
					<Particles count={90} seed={161} color="rgba(220,230,255,1)" size={[0.6, 2.2]} rise={[-2, -6]} drift={[-4, 4]} opacity={0.5} bokeh={0.2} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5B / 5H: una mano levantada contra la luz
export const Mano: React.FC<SceneProps & {sub?: string}> = ({plano, dur, sub}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	const v = sub ?? plano.id;
	const calm = v === '5H';
	const p = clamp(frame / Math.max(1, dur - 1));
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		const ctx = prep(c, W, H);
		const rise = calm ? 0.04 * easeOut(p) : 0.1 * easeOut(p);
		const args = {
			x: (calm ? 0.53 : 0.48) * W,
			y: (calm ? 0.8 : 0.9 - rise) * H,
			scale: (calm ? 0.42 : 0.5) * H,
			angle: calm ? 0.1 : -0.12 + p * 0.05,
			spread: calm ? 0.25 : 0.1 + p * 0.3,
			curl: calm ? 0.12 : 0.3 - p * 0.2,
		};
		ctx.save();
		ctx.filter = `blur(${H * 0.015}px)`;
		ctx.globalAlpha = 0.7;
		drawHand(ctx, {...args, fill: 'rgba(255,225,170,1)'});
		ctx.restore();
		drawHand(ctx, {...args, fill: '#04050a', rim: 'rgba(255,236,200,1)', rimPx: Math.max(2, H * 0.004)});
	}, [frame, p, calm]);
	const lx = calm ? 0.6 : 0.55;
	return (
		<AbsoluteFill style={{background: `radial-gradient(ellipse 70% 80% at ${lx * 100}% 10%, #ffffff 0%, #fff0d0 12%, #e9b86a 30%, #3a3448 60%, #0b1426 85%, #05060a 100%)`}}>
			<Camera move={{zoom: [1.0, 1.06], shake: calm ? 0 : 8, shakeDecay: 7}} durationInFrames={dur}>
				<Layer depth={0.3}>
					<AbsoluteFill
						style={{
							background: `repeating-conic-gradient(from 0deg at ${lx * 100}% 8%, rgba(255,255,255,0.10) 0deg 3deg, transparent 3deg 9deg)`,
							mixBlendMode: 'screen',
							transform: `rotate(${p * 4}deg)`,
							WebkitMaskImage: `radial-gradient(circle at ${lx * 100}% 8%, black 0%, transparent 70%)`,
						}}
					/>
				</Layer>
				<Layer depth={0.6}>
					<Particles count={110} seed={171} color="rgba(255,240,215,1)" size={[0.8, 2.6]} rise={[-5, -12]} drift={[-4, 4]} opacity={0.65} bokeh={0.3} />
				</Layer>
				<Layer depth={1.0}>
					<AbsoluteFill>
						<canvas ref={ref} style={{width: '100%', height: '100%'}} />
					</AbsoluteFill>
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5C: auditorio en penumbra, las luces se encienden
export const Auditorio: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	const t = frame / FPS;
	const ignite = [0.2, 0.5, 0.8, 1.1];
	const rowOn = (k: number) => {
		const d = t - ignite[k];
		if (d < 0) {
			return 0;
		}
		const flick = d < 0.08 ? (Math.floor(d * 75) % 2 === 0 ? 1 : 0.3) : 1;
		return Math.min(1, d / 0.05) * flick;
	};
	const lit = ignite.reduce((acc, _, k) => acc + rowOn(k), 0) / ignite.length;
	const seats = useMemo(() => {
		const r = makeRng(181);
		const rows: {y: number; h: number; heads: {x: number; s: number}[]}[] = [];
		for (let i = 0; i < 9; i++) {
			const y = 0.6 + Math.pow(i / 8, 1.4) * 0.45;
			const sc = 0.012 + (i / 8) * 0.05;
			const heads: {x: number; s: number}[] = [];
			const n = Math.round(14 + (8 - i) * 4);
			for (let k = 0; k < n; k++) {
				if (r() < 0.82) {
					heads.push({x: (k + 0.5 + (r() - 0.5) * 0.4) / n, s: sc * (0.9 + r() * 0.25)});
				}
			}
			rows.push({y, h: sc, heads});
		}
		return rows;
	}, []);
	useLayoutEffect(() => {
		const c = ref.current;
		if (!c) {
			return;
		}
		const ctx = prep(c, W, H);
		// escenario al fondo
		const sg = ctx.createRadialGradient(W * 0.5, H * 0.5, 0, W * 0.5, H * 0.5, W * 0.45);
		sg.addColorStop(0, `rgba(80,110,190,${0.12 + lit * 0.4})`);
		sg.addColorStop(1, 'rgba(0,0,0,0)');
		ctx.fillStyle = sg;
		ctx.fillRect(0, 0, W, H);
		ctx.fillStyle = `rgba(20,28,48,${0.5 + lit * 0.3})`;
		ctx.fillRect(W * 0.22, H * 0.46, W * 0.56, H * 0.1);
		// filas de focos en el techo (perspectiva) con haces hacia abajo
		for (let k = 0; k < 4; k++) {
			const on = rowOn(k);
			const y = H * (0.05 + k * 0.075);
			const n = 9 + k * 2;
			const span = 0.5 + k * 0.12;
			for (let i = 0; i < n; i++) {
				const x = W * (0.5 + (i / (n - 1) - 0.5) * span);
				if (on > 0) {
					ctx.globalCompositeOperation = 'lighter';
					const bh = H * (0.55 - k * 0.05);
					const g = ctx.createLinearGradient(x, y, x, y + bh);
					g.addColorStop(0, `rgba(230,236,255,${0.22 * on})`);
					g.addColorStop(1, 'rgba(0,0,0,0)');
					ctx.fillStyle = g;
					ctx.beginPath();
					ctx.moveTo(x - 3, y);
					ctx.lineTo(x + 3, y);
					ctx.lineTo(x + bh * 0.16, y + bh);
					ctx.lineTo(x - bh * 0.16, y + bh);
					ctx.closePath();
					ctx.fill();
					const rg = ctx.createRadialGradient(x, y, 0, x, y, 26 + k * 6);
					rg.addColorStop(0, `rgba(255,255,255,${on})`);
					rg.addColorStop(0.25, `rgba(220,230,255,${0.6 * on})`);
					rg.addColorStop(1, 'rgba(0,0,0,0)');
					ctx.fillStyle = rg;
					ctx.fillRect(x - 40, y - 40, 80, 80);
					ctx.globalCompositeOperation = 'source-over';
				} else {
					ctx.fillStyle = 'rgba(30,34,44,1)';
					ctx.beginPath();
					ctx.arc(x, y, 3 + k, 0, Math.PI * 2);
					ctx.fill();
				}
			}
		}
		// filas de butacas con público (siluetas)
		for (const row of seats) {
			const y = row.y * H;
			ctx.fillStyle = '#03040a';
			ctx.fillRect(0, y, W, H - y);
			for (const hd of row.heads) {
				const x = hd.x * W;
				const s = hd.s * H;
				ctx.beginPath();
				ctx.ellipse(x, y - s * 0.9, s * 0.42, s * 0.52, 0, 0, Math.PI * 2);
				ctx.fill();
				ctx.beginPath();
				ctx.ellipse(x, y - s * 0.1, s * 0.9, s * 0.5, 0, Math.PI, 0);
				ctx.fill();
			}
			// borde iluminado por los focos
			if (lit > 0) {
				ctx.fillStyle = `rgba(150,170,230,${0.12 * lit})`;
				ctx.fillRect(0, y, W, Math.max(1, row.h * H * 0.08));
			}
		}
	}, [frame, lit, seats]);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.05], shake: 8, shakeDecay: 7}} durationInFrames={dur}>
				<Layer depth={0.6}>
					<Fog tex={1} color="#8ea4dc" opacity={0.1 + lit * 0.3} speed={15} top={0.1} bottom={0.7} />
				</Layer>
				<Layer depth={1.0}>
					<AbsoluteFill>
						<canvas ref={ref} style={{width: '100%', height: '100%'}} />
					</AbsoluteFill>
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5D: fondo de "DESPIERTA"
export const PalabraFondo: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const p = clamp(frame / Math.max(1, dur - 1));
	const shake = Math.exp(-frame / 6) * 10;
	return (
		<AbsoluteFill
			style={{
				background: 'radial-gradient(ellipse at 50% 50%, #1a2a50 0%, #0b1426 40%, #05060a 80%)',
				transform: `translate(${Math.sin(frame * 2.1) * shake}px, ${Math.cos(frame * 1.7) * shake}px) scale(1.02)`,
			}}
		>
			<AbsoluteFill
				style={{
					background: 'repeating-conic-gradient(from 0deg at 50% 50%, rgba(170,200,255,0.12) 0deg 2.5deg, transparent 2.5deg 10deg)',
					transform: `rotate(${p * 6}deg) scale(1.4)`,
					mixBlendMode: 'screen',
					WebkitMaskImage: 'radial-gradient(circle at 50% 50%, black 0%, transparent 65%)',
				}}
			/>
			<Glow x={0.5} y={0.5} r={600} color="#9fbaff" opacity={0.4 * (1.2 - p * 0.4)} />
			<Streak x={0.5} y={0.5} width={1.8} opacity={0.6} color="#a8c6ff" />
			<Particles count={200} seed={191} color="rgba(220,232,255,1)" size={[0.6, 2.4]} rise={[0, 0]} drift={[0, 0]} opacity={0.8} burst={{x: 0.5, y: 0.5, atSec: 0, strength: 0.35}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5L: montaje final con destellos
export const Montaje: React.FC<SceneProps> = ({plano, dur}) => {
	const frame = useCurrentFrame();
	const cut = Math.round(dur / 4);
	const p = clamp(frame / Math.max(1, dur - 1));
	const white = easeIn(clamp((p - 0.86) / 0.14));
	const sub = (id: string, inicio: number) => ({...plano, id, inicio});
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Sequence durationInFrames={cut}>
				<Adoracion plano={sub('5G', plano.inicio)} dur={cut} sub="5G" />
			</Sequence>
			<Sequence from={cut} durationInFrames={cut}>
				<Mano plano={sub('5B', plano.inicio)} dur={cut} sub="5B" />
			</Sequence>
			<Sequence from={cut * 2} durationInFrames={cut}>
				<Adoracion plano={sub('5J', plano.inicio)} dur={cut} sub="5J" />
			</Sequence>
			<Sequence from={cut * 3}>
				<Amanecer plano={sub('5K', plano.inicio)} dur={dur - cut * 3} />
			</Sequence>
			<AbsoluteFill style={{background: '#fff', opacity: white}} />
		</AbsoluteFill>
	);
};
