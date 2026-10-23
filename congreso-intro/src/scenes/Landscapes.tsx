import React, {useMemo} from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';
import {FPS, PAL, PLATES, Plano} from '../config';
import {Camera, Layer} from '../components/Camera';
import {Fog, Glow, Streak} from '../components/Effects';
import {Figures, FigureSpec} from '../components/Figures';
import {Particles} from '../components/Particles';
import {PlateScene, plateUrl} from '../components/PlateScene';
import {basePose, walkPose} from '../lib/figure';
import {clamp, easeIn, easeOut} from '../lib/rng';

export type SceneProps = {plano: Plano; dur: number};

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const meta = (env: string) => PLATES[env] ?? {};
const num = (v: unknown, d: number) => (typeof v === 'number' ? v : d);
const pt = (v: unknown, d: [number, number]): [number, number] => (Array.isArray(v) && v.length === 2 ? [v[0] as number, v[1] as number] : d);

// ------------------------------------------------------------------ 1A: el silencio
export const VoidDust: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const shaft = interpolate(frame, [12, 100, dur - 25, dur], [0, 1, 1, 0.5], CL);
	const mask = 'linear-gradient(104deg, transparent 16%, black 38%, black 62%, transparent 84%)';
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.1], x: [0.01, -0.01]}} durationInFrames={dur}>
				<Layer depth={0.3}>
					<AbsoluteFill
						style={{
							background:
								'linear-gradient(104deg, transparent 18%, rgba(90,120,210,0.06) 32%, rgba(170,195,255,0.16) 44%, rgba(225,232,255,0.26) 50%, rgba(170,195,255,0.16) 56%, rgba(90,120,210,0.06) 68%, transparent 82%)',
							opacity: shaft,
						}}
					/>
				</Layer>
				<Layer depth={0.7} style={{WebkitMaskImage: mask}}>
					<Particles count={420} seed={11} color="rgba(225,232,255,1)" size={[0.8, 2.8]} rise={[-2, -8]} drift={[-4, 4]} opacity={1.0 * shaft} bokeh={0.12} twinkle={0.5} />
				</Layer>
				<Layer depth={1.2}>
					<Particles count={40} seed={12} color="rgba(190,205,255,1)" size={[1, 3]} rise={[-3, -6]} drift={[-2, 2]} opacity={0.35 * shaft} bokeh={0.6} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 1B: horizonte
export const Horizonte: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const reveal = interpolate(frame, [0, dur * 0.7], [0, 1], CL);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.1], y: [0.03, -0.005]}} durationInFrames={dur}>
				<PlateScene
					env="horizonte"
					between={{
						1: <Fog tex={0} color="#5a6a9a" opacity={0.18} speed={8} top={0.42} bottom={0.75} scale={1.3} />,
					}}
				/>
				<Layer depth={0.22}>
					<Glow x={0.5} y={0.47} r={900} color="rgba(120,150,230,1)" opacity={0.18 * reveal} />
					<Glow x={0.52} y={0.46} r={260} color={PAL.dorado} opacity={0.14 * reveal} />
					<Streak x={0.52} y={0.462} width={0.9} opacity={0.25 * reveal} color="#7aa0ff" />
				</Layer>
				<Layer depth={1.0}>
					<Particles count={90} seed={21} color="rgba(200,215,255,1)" size={[0.6, 1.8]} rise={[-1, -4]} drift={[-3, 3]} opacity={0.5} bokeh={0.15} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 2A: ciudad monumental
export const CiudadAerea: React.FC<SceneProps> = ({dur}) => {
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.02, 1.1], x: [-0.012, 0.018], roll: [-1.2, 0.4]}} durationInFrames={dur}>
				<PlateScene env="ciudad_aerea" />
				<Layer depth={0.5}>
					<Fog tex={1} color="#3a4466" opacity={0.22} speed={14} top={0.25} bottom={0.55} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 2B: calle, joven caminando solo
export const Calle: React.FC<SceneProps> = ({dur}) => {
	const fig: FigureSpec[] = useMemo(
		() => [
			{
				x: 0.47,
				y: 0.965,
				h: 0.5,
				view: 'front',
				pose: (t: number) => ({...walkPose(Math.PI / 2 + ((t - 0.25) * 2 * Math.PI) / 1.1, 0.9), head: -0.05}),
				styleSeed: 4,
				style: {hair: 'hood', clothing: 'hoodie', female: false, build: 1.05},
				rim: 'rgba(255,190,120,0.95)',
				rimDir: [0, -1],
				vy: -0.022,
				grow: -0.03,
			},
		],
		[],
	);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.13], y: [0.0, -0.01]}} durationInFrames={dur}>
				<PlateScene env="calle" />
				<Layer depth={0.6}>
					<Fog tex={0} color="#6a5a50" opacity={0.16} speed={10} top={0.3} bottom={0.75} />
				</Layer>
				<Layer depth={1.0}>
					<Figures figures={fig} glow={{color: 'rgba(255,170,90,1)', blur: 6, opacity: 0.35}} />
				</Layer>
				<Layer depth={1.3}>
					<Particles count={60} seed={31} color="rgba(255,200,150,1)" size={[0.6, 2]} rise={[2, 6]} drift={[-3, 3]} opacity={0.35} bokeh={0.25} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 2C: azotea, siluetas mirando una luz lejana
export const Azotea: React.FC<SceneProps> = ({dur}) => {
	const m = meta('skyline');
	const ay = num(m.azotea_y, 0.82);
	const luz = pt(m.luz, [0.66, 0.49]);
	const figs: FigureSpec[] = useMemo(
		() =>
			[0.36, 0.45, 0.555].map((x, i) => ({
				x,
				y: ay + 0.003,
				h: [0.31, 0.29, 0.33][i],
				view: 'front' as const,
				pose: (t: number) => ({...basePose(), head: 0.06 + 0.03 * Math.sin(t * 0.6 + i), ls: 0.06, rs: i === 1 ? 0.25 : 0.06, re: i === 1 ? -1.6 : 0.06}),
				styleSeed: 40 + i,
				rim: 'rgba(255,215,160,0.9)',
				rimDir: [0.5, -0.8] as [number, number],
			})),
		[ay],
	);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.04, 1.1], x: [0.02, -0.02]}} durationInFrames={dur}>
				<PlateScene
					env="skyline"
					depths={[1.0, 0.25]}
					front={
						<Layer depth={1.0}>
							<Figures figures={figs} glow={{color: 'rgba(255,200,140,1)', blur: 5, opacity: 0.3}} />
						</Layer>
					}
				/>
				<Layer depth={0.25}>
					<Glow x={luz[0]} y={luz[1]} r={140} color="#fff3dc" opacity={0.55} />
					<Streak x={luz[0]} y={luz[1]} width={1.2} opacity={0.45} color="#ffd8a0" />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 2D / 3F / 5I: acantilado
export const Acantilado: React.FC<SceneProps> = ({plano, dur}) => {
	const frame = useCurrentFrame();
	const variant = plano.id;
	const env = variant === '5I' ? 'acantilado_luz' : 'acantilado';
	const m = meta(env);
	const luz = pt(m.luz, [0.35, 0.36]);
	const fp = pt(m.figura, [0.4, 0.79]);
	const t = frame / FPS;
	const walking = variant === '5I';
	const figs: FigureSpec[] = useMemo(
		() => [
			walking
				? {
						x: fp[0] - 0.12,
						y: fp[1],
						h: 0.2,
						view: 'side' as const,
						facing: 1 as const,
						pose: (tt: number) => walkPose(tt * 5.2, 0.85),
						styleSeed: 7,
						style: {hair: 'short', clothing: 'jacket', female: false},
						rim: 'rgba(255,225,170,1)',
						rimDir: [-0.4, -0.9] as [number, number],
						vx: 0.035,
					}
				: {
						x: fp[0],
						y: fp[1] + 0.004,
						h: 0.205,
						view: 'front' as const,
						pose: (tt: number) => ({...basePose(), head: 0.12 + Math.min(0.12, tt * 0.04), sway: 0.002 * Math.sin(tt)}),
						styleSeed: 7,
						style: {hair: 'short', clothing: 'jacket', female: false},
						rim: 'rgba(255,225,170,1)',
						rimDir: [-0.4, -0.9] as [number, number],
					},
		],
		[fp, walking],
	);
	const mv =
		variant === '3F'
			? {zoom: [1.28, 1.36] as [number, number], x: [(luz[0] - 0.5) * 0.05, (luz[0] - 0.5) * 0.09] as [number, number], ease: (x: number) => x}
			: variant === '5I'
				? {zoom: [1.06, 1.2] as [number, number], x: [0, (luz[0] - 0.5) * 0.08] as [number, number]}
				: {zoom: [1.0, 1.14] as [number, number], x: [0, (luz[0] - 0.5) * 0.1] as [number, number]};
	const bright = variant === '3F' ? 1.12 : 1;
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={mv} durationInFrames={dur}>
				<PlateScene
					env={env}
					raysOpacity={variant === '2D' ? interpolate(t, [0, 1.2], [0.6, 1], CL) : 1}
					filter={bright !== 1 ? `brightness(${bright})` : undefined}
					between={{
						1: <Fog tex={1} color="#c8b090" opacity={0.2} speed={18} top={0.5} bottom={0.85} />,
					}}
					front={
						<Layer depth={1.25}>
							<Figures figures={figs} glow={{color: 'rgba(255,215,160,1)', blur: 7, opacity: 0.45}} />
						</Layer>
					}
				/>
				<Layer depth={0.3}>
					<Glow x={luz[0]} y={luz[1]} r={380} color={PAL.dorado} opacity={0.25} />
				</Layer>
				<Layer depth={0.9}>
					<Particles count={140} seed={51} color="rgba(255,225,180,1)" size={[0.6, 2.4]} rise={[-3, -10]} drift={[-6, 2]} opacity={0.6} bokeh={0.12} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3A: tormenta (timelapse)
export const Tormenta: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const flash = (at: number) => {
		const d = t - at;
		if (d < 0 || d > 0.5) {
			return 0;
		}
		return Math.exp(-d * 14) * 0.9 + (d > 0.12 && d < 0.2 ? 0.5 : 0);
	};
	const lightning = Math.min(1, flash(0.3) + flash(2.6) * 0.8);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.02, 1.12], y: [0.01, -0.02]}} durationInFrames={dur}>
				<PlateScene
					env="tormenta"
					between={{
						1: (
							<>
								<Layer depth={0.22}>
									<Fog tex={0} color="#1a2030" opacity={0.55} speed={160} top={0} bottom={0.55} scale={1.4} blend="multiply" feather={0.1} />
									<Fog tex={1} color="#8090b0" opacity={0.16} speed={110} top={0} bottom={0.5} scale={1.1} feather={0.1} />
								</Layer>
							</>
						),
					}}
				/>
				<AbsoluteFill style={{background: 'radial-gradient(ellipse at 40% 25%, rgba(200,215,255,1), rgba(120,140,200,0.4) 50%, transparent 80%)', opacity: lightning * 0.5, mixBlendMode: 'screen'}} />
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3C / 3H: cumbre
export const Cumbre: React.FC<SceneProps> = ({plano, dur}) => {
	const quick = plano.id === '3H';
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={quick ? {zoom: [1.16, 1.22], y: [0.0, -0.015], ease: (x) => x} : {zoom: [1.03, 1.1], y: [0.05, -0.02]}} durationInFrames={dur}>
				<PlateScene env="cumbre" />
				<Layer depth={0.2}>
					<Glow x={-0.05} y={0.5} r={900} color={PAL.dorado} opacity={0.22} />
				</Layer>
				<Layer depth={0.8}>
					<Particles count={70} seed={61} color="rgba(255,230,200,1)" size={[0.6, 1.8]} rise={[-2, -5]} drift={[4, 10]} opacity={0.45} bokeh={0.1} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3D / 5E: caminantes
export const Caminantes: React.FC<SceneProps> = ({plano, dur}) => {
	const toward = plano.id === '5E';
	const m = meta(toward ? 'campo' : 'cresta');
	const ground = (m.suelo0 as number[] | undefined) ?? [];
	const figs: FigureSpec[] = useMemo(() => {
		if (toward) {
			const xs = [0.38, 0.45, 0.5, 0.56, 0.63, 0.42, 0.59];
			const ys = [0.86, 0.9, 0.84, 0.89, 0.86, 0.95, 0.96];
			const hs = [0.36, 0.42, 0.34, 0.41, 0.35, 0.5, 0.52];
			return xs.map((x, i) => ({
				x,
				y: ys[i],
				h: hs[i],
				view: 'front' as const,
				pose: (t: number) => walkPose(t * 3.4 + i * 1.7, 0.75),
				styleSeed: 70 + i,
				rim: 'rgba(255,215,150,1)',
				rimDir: [0, -1] as [number, number],
				grow: 0.06,
				vy: 0.004,
			}));
		}
		const xs = [0.16, 0.24, 0.31, 0.4, 0.47];
		return xs.map((x, i) => ({
			x,
			y: 0.6,
			h: [0.13, 0.125, 0.135, 0.12, 0.13][i],
			view: 'side' as const,
			facing: 1 as const,
			pose: (t: number) => walkPose(t * 5.6 + i * 2.1, 0.95),
			styleSeed: 80 + i,
			rim: 'rgba(255,215,160,1)',
			rimDir: [-0.6, -0.8] as [number, number],
			vx: 0.028,
			ground,
		}));
	}, [toward, ground]);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={toward ? {zoom: [1.0, 1.06]} : {zoom: [1.02, 1.07], x: [-0.01, 0.015]}} durationInFrames={dur}>
				<PlateScene
					env={toward ? 'campo' : 'cresta'}
					depths={toward ? [0.9, 0.25] : [1.0, 0.25]}
					between={
						toward
							? {}
							: {
									0: (
										<Layer depth={1.0}>
											<Figures figures={figs} glow={{color: 'rgba(255,200,140,1)', blur: 4, opacity: 0.45}} />
										</Layer>
									),
								}
					}
					front={
						toward ? (
							<Layer depth={0.95}>
								<Figures figures={figs} glow={{color: 'rgba(255,200,130,1)', blur: 9, opacity: 0.55}} />
							</Layer>
						) : null
					}
				/>
				<Layer depth={0.9}>
					<Particles count={80} seed={71} color="rgba(255,225,180,1)" size={[0.6, 2.0]} rise={[-2, -6]} drift={[-4, 4]} opacity={0.5} bokeh={0.2} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3E: rayos
export const Rayos: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const m = meta('rayos');
	const luz = pt(m.luz, [0.47, 0.25]);
	const k = interpolate(frame, [0, dur], [0.6, 1.0], CL);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.0, 1.22], x: [0, (luz[0] - 0.5) * 0.12], y: [0, (luz[1] - 0.5) * 0.1]}} durationInFrames={dur}>
				<PlateScene env="rayos" raysOpacity={k} />
				<Layer depth={0.3}>
					<Glow x={luz[0]} y={luz[1]} r={420} color="#fff1d6" opacity={0.3 * k} />
				</Layer>
				<Layer depth={1.0}>
					<Particles count={160} seed={81} color="rgba(255,235,200,1)" size={[0.6, 2.4]} rise={[-4, -10]} drift={[-5, 5]} opacity={0.6} bokeh={0.12} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3G: travesía entre nubes
export const Nubes: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const p = frame / Math.max(1, dur - 1);
	const capas = meta('cielo').capas ?? ['capa0.jpg'];
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<AbsoluteFill style={{transform: `scale(${1.1 + p * 0.45})`}}>
				<Img src={plateUrl('cielo', capas[capas.length - 1])} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
			</AbsoluteFill>
			{[0, 1, 2].map((i) => {
				const q = (p + i / 3) % 1;
				return (
					<AbsoluteFill key={i} style={{transform: `scale(${0.8 + q * 2.4})`, opacity: Math.sin(q * Math.PI) * 0.7}}>
						<Fog tex={(i % 2) as 0 | 1} color="#f2e6d6" opacity={1} speed={0} scale={0.8} feather={0.2} />
					</AbsoluteFill>
				);
			})}
			<Glow x={0.5} y={0.42} r={500} color="#fff6e6" opacity={0.35 + p * 0.25} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 3J: transición de luz
export const Transicion: React.FC<SceneProps> = ({dur}) => {
	const frame = useCurrentFrame();
	const p = clamp(frame / Math.max(1, dur - 1));
	const g = easeIn(p);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Glow x={0.5} y={0.5} r={220 + g * 1300} color="#fff3dd" opacity={0.3 + g * 0.75} />
			<Glow x={0.5} y={0.5} r={70 + g * 280} color="#ffffff" opacity={0.45 + g * 0.55} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse 70% 50% at 50% 50%, rgba(79,140,255,0.12), transparent 70%)'}} />
			<Streak x={0.5} y={0.5} width={0.3 + g * 1.6} opacity={0.4 + g * 0.6} color="#a8c6ff" />
			<Particles
				count={220}
				seed={91}
				color="rgba(255,240,215,1)"
				size={[0.6, 2.6]}
				rise={[0, 0]}
				drift={[0, 0]}
				opacity={0.8}
				bokeh={0.1}
				burst={{x: 0.5, y: 0.5, atSec: 0, strength: 0.15 + g * 0.6}}
			/>
			<AbsoluteFill style={{background: '#fff', opacity: easeIn(clamp((p - 0.82) / 0.18)) * 0.9}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 4A: cielo inmenso (versículo)
export const Cielo: React.FC<SceneProps> = ({dur}) => {
	const m = meta('cielo');
	const luz = pt(m.luz, [0.5, 0.25]);
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={{zoom: [1.12, 1.0], y: [0.035, -0.02], ease: easeOut}} durationInFrames={dur}>
				<PlateScene env="cielo" />
				<Layer depth={0.3}>
					<Glow x={luz[0]} y={luz[1]} r={500} color={PAL.dorado} opacity={0.25} />
				</Layer>
				<Layer depth={0.9}>
					<Particles count={150} seed={101} color="rgba(255,225,170,1)" size={[0.6, 2.2]} rise={[-2, -6]} drift={[-3, 3]} opacity={0.55} bokeh={0.12} />
				</Layer>
			</Camera>
			<AbsoluteFill style={{background: 'radial-gradient(ellipse 62% 42% at 50% 52%, rgba(5,6,10,0.72), rgba(5,6,10,0.25) 70%, transparent 100%)'}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 5F / 5K: amanecer
export const Amanecer: React.FC<SceneProps> = ({plano, dur}) => {
	const frame = useCurrentFrame();
	const fast = plano.id === '5K';
	const m = meta('amanecer');
	const luz = pt(m.luz, [0.5, 0.48]);
	const b = fast ? interpolate(frame, [0, dur], [1, 1.5], CL) : 1;
	return (
		<AbsoluteFill style={{background: PAL.negro}}>
			<Camera move={fast ? {zoom: [1.1, 1.38], x: [0, (luz[0] - 0.5) * 0.2], y: [0, (luz[1] - 0.5) * 0.2], ease: easeIn} : {zoom: [1.0, 1.07]}} durationInFrames={dur}>
				<PlateScene env="amanecer" filter={b !== 1 ? `brightness(${b})` : undefined} between={{1: <Fog tex={1} color="#ffd8a0" opacity={0.18} speed={20} top={0.5} bottom={0.9} />}} />
				<Layer depth={0.25}>
					<Glow x={luz[0]} y={luz[1]} r={520} color="#ffe2b0" opacity={0.35} />
					<Streak x={luz[0]} y={luz[1]} width={1.5} opacity={0.5} color="#ffd9a8" />
				</Layer>
				<Layer depth={1.0}>
					<Particles count={120} seed={111} color="rgba(255,225,180,1)" size={[0.6, 2.2]} rise={[-3, -8]} drift={[-4, 4]} opacity={0.55} bokeh={0.15} />
				</Layer>
			</Camera>
		</AbsoluteFill>
	);
};
