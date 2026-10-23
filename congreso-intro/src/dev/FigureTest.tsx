import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {basePose, drawLitFigure, randomStyle, walkPose, worshipPose} from '../lib/figure';

export const FigureTest: React.FC = () => {
	const frame = useCurrentFrame();
	const ref = useRef<HTMLCanvasElement>(null);
	useLayoutEffect(() => {
		const c = ref.current!;
		const ctx = c.getContext('2d')!;
		ctx.clearRect(0, 0, 1920, 1080);
		const g = ctx.createLinearGradient(0, 0, 0, 1080);
		g.addColorStop(0, '#2a3550');
		g.addColorStop(0.7, '#c9a06a');
		g.addColorStop(1, '#3a2c20');
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, 1920, 1080);
		const t = frame / 30;
		// fila 1: frontal de pie / adoración / mirando arriba
		for (let i = 0; i < 8; i++) {
			const st = randomStyle(i + 1);
			const pose = i < 2 ? basePose() : i < 6 ? worshipPose(t, i) : {...basePose(), head: 0.35};
			drawLitFigure(ctx, {x: 140 + i * 230, y: 480, h: 380, view: 'front', pose, style: st, fill: '#07090f', rim: '#ffd9a0'});
		}
		// fila 2: lateral caminando (fases) y frontal caminando
		for (let i = 0; i < 8; i++) {
			const st = randomStyle(i + 20);
			const ph = (i / 8) * Math.PI * 2 + t * 6;
			const view = i < 5 ? 'side' : 'front';
			drawLitFigure(ctx, {x: 140 + i * 230, y: 1010, h: 400, view, facing: 1, pose: walkPose(ph), style: st, fill: '#07090f', rim: '#ffd9a0'});
		}
	}, [frame]);
	return (
		<AbsoluteFill>
			<canvas ref={ref} width={1920} height={1080} />
		</AbsoluteFill>
	);
};
