import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {FPS, PLATES} from '../config';
import {Layer} from './Camera';

/** Profundidades por defecto según la posición de la capa (0 = la más cercana). */
const defaultDepth = (i: number, n: number, name: string) => {
	if (name.startsWith('roca')) {
		return 1.25;
	}
	if (i === n - 1) {
		return 0.22;
	}
	const k = i / Math.max(1, n - 2);
	return 1.0 - k * 0.55;
};

export const plateUrl = (env: string, file: string) => staticFile(`images/plates/${env}/${file}`);

/**
 * Monta las capas de un paisaje generado (de lejos a cerca) con parallax.
 * between: elementos a insertar delante de una capa concreta (índice de capa desde la más cercana).
 */
export const PlateScene: React.FC<{
	env: string;
	depths?: number[];
	raysOpacity?: number;
	raysPulse?: boolean;
	between?: Record<number, React.ReactNode>;
	front?: React.ReactNode;
	filter?: string;
}> = ({env, depths, raysOpacity = 1, raysPulse = true, between = {}, front, filter}) => {
	const frame = useCurrentFrame();
	const meta = PLATES[env];
	const capas = meta?.capas ?? [];
	const n = capas.length;
	const far = capas[n - 1];
	const pulse = raysPulse ? 0.85 + 0.15 * Math.sin((frame / FPS) * 0.9) : 1;
	const order = capas.map((c, i) => ({c, i})).reverse();
	return (
		<AbsoluteFill style={{filter}}>
			{order.map(({c, i}) => {
				const d = depths?.[i] ?? defaultDepth(i, n, c);
				return (
					<React.Fragment key={c}>
						<Layer depth={d}>
							<Img src={plateUrl(env, c)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
						</Layer>
						{c === far && meta?.rayos ? (
							<Layer depth={d} blend="screen" opacity={raysOpacity * pulse}>
								<Img src={plateUrl(env, meta.rayos)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
							</Layer>
						) : null}
						{between[i] ?? null}
					</React.Fragment>
				);
			})}
			{front}
		</AbsoluteFill>
	);
};
