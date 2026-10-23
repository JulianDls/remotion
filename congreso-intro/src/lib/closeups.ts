/** Primeros planos en silueta: perfil de un joven y mano levantada (canvas 2D). */
type Pt = [number, number];

/** Traza una curva suave (cuadráticas por puntos medios) cerrada. */
const smoothPath = (ctx: CanvasRenderingContext2D, pts: Pt[], X: (p: Pt) => Pt) => {
	const P = pts.map(X);
	const n = P.length;
	const mid = (i: number): Pt => [(P[i % n][0] + P[(i + 1) % n][0]) / 2, (P[i % n][1] + P[(i + 1) % n][1]) / 2];
	ctx.beginPath();
	const m0 = mid(n - 1);
	ctx.moveTo(m0[0], m0[1]);
	for (let i = 0; i < n; i++) {
		const m = mid(i);
		ctx.quadraticCurveTo(P[i][0], P[i][1], m[0], m[1]);
	}
	ctx.closePath();
};

// Perfil mirando a la derecha. Unidad = altura de la cabeza (coronilla-barbilla ≈ 1).
// Origen en el centro del cráneo (a la altura de la oreja); y hacia abajo.
const HEAD: Pt[] = [
	[0.04, -0.63], [0.22, -0.6], [0.34, -0.51], [0.41, -0.38], [0.44, -0.24], [0.455, -0.14], [0.43, -0.085],
	[0.445, -0.05], [0.5, 0.02], [0.555, 0.075], [0.545, 0.1], [0.495, 0.115], [0.455, 0.125], [0.47, 0.155],
	[0.468, 0.18], [0.445, 0.198], [0.462, 0.222], [0.455, 0.25], [0.432, 0.275], [0.448, 0.315], [0.44, 0.355],
	[0.4, 0.39], [0.32, 0.41], [0.22, 0.415], [0.17, 0.46], [0.16, 0.62], [0.19, 0.82],
	[-0.26, 0.82], [-0.23, 0.6], [-0.24, 0.42], [-0.32, 0.26], [-0.42, 0.06], [-0.46, -0.16], [-0.4, -0.4], [-0.26, -0.56], [-0.1, -0.63],
];
// Pelo corto con volumen arriba y nuca
const HAIR: Pt[] = [
	[0.0, -0.69], [0.2, -0.67], [0.34, -0.58], [0.43, -0.46], [0.45, -0.36], [0.38, -0.39], [0.3, -0.44],
	[0.2, -0.47], [0.06, -0.44], [-0.08, -0.36], [-0.2, -0.18], [-0.26, 0.04], [-0.3, 0.2], [-0.38, 0.16],
	[-0.47, -0.06], [-0.48, -0.3], [-0.4, -0.5], [-0.24, -0.64],
];
const SHOULDERS: Pt[] = [
	[0.18, 0.72], [0.3, 0.86], [0.52, 0.98], [0.66, 1.15], [0.72, 1.6], [-1.3, 1.6], [-1.15, 1.08], [-0.85, 0.92], [-0.5, 0.84], [-0.28, 0.74],
];

export const drawProfile = (
	ctx: CanvasRenderingContext2D,
	o: {x: number; y: number; scale: number; tilt: number; fill: string; rim: string; rimPx: number; hairStrands?: number; t: number},
) => {
	const {x, y, scale: s, tilt} = o;
	// pivote del giro de la cabeza: parte alta del cuello
	const pv: Pt = [-0.04, 0.5];
	const cs = Math.cos(-tilt);
	const sn = Math.sin(-tilt);
	const Xh = (p: Pt): Pt => {
		const dx = p[0] - pv[0];
		const dy = p[1] - pv[1];
		return [x + (pv[0] + dx * cs - dy * sn) * s, y + (pv[1] + dx * sn + dy * cs) * s];
	};
	const Xb = (p: Pt): Pt => [x + p[0] * s, y + p[1] * s];
	const drawAll = (fill: string, dx: number, dy: number) => {
		ctx.fillStyle = fill;
		const sh = (f: (p: Pt) => Pt) => (p: Pt): Pt => {
			const q = f(p);
			return [q[0] + dx, q[1] + dy];
		};
		smoothPath(ctx, SHOULDERS, sh(Xb));
		ctx.fill();
		smoothPath(ctx, HEAD, sh(Xh));
		ctx.fill();
		smoothPath(ctx, HAIR, sh(Xh));
		ctx.fill();
		// mechones finos en la parte superior (captan la luz)
		const n = o.hairStrands ?? 22;
		ctx.strokeStyle = fill;
		ctx.lineCap = 'round';
		for (let i = 0; i < n; i++) {
			const u = i / (n - 1);
			const ang = Math.PI * (0.95 - u * 0.75);
			const bx = Math.cos(ang) * 0.44;
			const by = -0.18 - Math.sin(ang) * 0.48;
			const len = 0.035 + ((i * 53) % 9) * 0.006;
			const sway = Math.sin(o.t * 1.7 + i * 1.3) * 0.01;
			const out: Pt = [bx + Math.cos(ang - 0.25) * len + sway, by - Math.sin(ang - 0.25) * len];
			const p0 = sh(Xh)([bx, by]);
			const p1 = sh(Xh)(out);
			ctx.lineWidth = Math.max(0.6, s * 0.0035);
			ctx.beginPath();
			ctx.moveTo(p0[0], p0[1]);
			ctx.quadraticCurveTo((p0[0] * 0.4 + p1[0] * 0.6) + s * 0.004, (p0[1] * 0.4 + p1[1] * 0.6) - s * 0.006, p1[0], p1[1]);
			ctx.stroke();
		}
	};
	drawAll(o.rim, 0, 0);
	drawAll(o.fill, -o.rimPx, o.rimPx * 0.55);
};

/** Mano abierta y alzada vista por el dorso (unidad = largo de la mano; origen en la muñeca). */
export const drawHand = (
	ctx: CanvasRenderingContext2D,
	o: {x: number; y: number; scale: number; angle: number; spread: number; curl: number; fill: string; rim?: string; rimPx?: number},
) => {
	const {x, y, scale: s} = o;
	const ca = Math.cos(o.angle);
	const sa = Math.sin(o.angle);
	const T = (p: Pt): Pt => [x + (p[0] * ca - p[1] * sa) * s, y + (p[0] * sa + p[1] * ca) * s];
	const disc = (c: Pt, r: number) => {
		const C = T(c);
		ctx.beginPath();
		ctx.arc(C[0], C[1], r * s, 0, Math.PI * 2);
		ctx.fill();
	};
	const cap = (a: Pt, b: Pt, ra: number, rb: number) => {
		const A = T(a);
		const B = T(b);
		const dx = B[0] - A[0];
		const dy = B[1] - A[1];
		const l = Math.hypot(dx, dy) || 1e-6;
		const nx = -dy / l;
		const ny = dx / l;
		ctx.beginPath();
		ctx.moveTo(A[0] + nx * ra * s, A[1] + ny * ra * s);
		ctx.lineTo(B[0] + nx * rb * s, B[1] + ny * rb * s);
		ctx.lineTo(B[0] - nx * rb * s, B[1] - ny * rb * s);
		ctx.lineTo(A[0] - nx * ra * s, A[1] - ny * ra * s);
		ctx.closePath();
		ctx.fill();
		disc(a, ra);
		disc(b, rb);
	};
	const draw = (fill: string, ox: number, oy: number) => {
		ctx.fillStyle = fill;
		ctx.save();
		ctx.translate(ox, oy);
		// dorso de la mano, muñeca y antebrazo en un solo contorno continuo
		smoothPath(
			ctx,
			[
				[0.235, -0.47], [0.255, -0.33], [0.24, -0.18], [0.17, -0.03], [0.18, 0.3], [0.23, 0.9], [0.28, 1.9],
				[-0.25, 1.9], [-0.2, 0.9], [-0.165, 0.3], [-0.155, -0.03], [-0.215, -0.12], [-0.24, -0.25], [-0.22, -0.4],
				[-0.19, -0.49], [-0.1, -0.545], [0.0, -0.56], [0.11, -0.548], [0.2, -0.51],
			],
			T,
		);
		ctx.fill();
		// dedos: [base, ángulo base, largos de falanges, radio en la base]
		const sp = o.spread;
		const fingers: [Pt, number, number[], number][] = [
			[[-0.15, -0.5], -0.13 - 0.18 * sp, [0.2, 0.125, 0.095], 0.048],
			[[-0.045, -0.54], -0.03 - 0.06 * sp, [0.225, 0.14, 0.1], 0.05],
			[[0.06, -0.53], 0.06 + 0.08 * sp, [0.21, 0.13, 0.095], 0.047],
			[[0.163, -0.49], 0.16 + 0.2 * sp, [0.16, 0.1, 0.08], 0.04],
		];
		for (const [base, ang0, lens, w] of fingers) {
			let p = base;
			let a = ang0;
			for (let k = 0; k < 3; k++) {
				const q: Pt = [p[0] + Math.sin(a) * lens[k], p[1] - Math.cos(a) * lens[k]];
				const ra = w * (1 - k * 0.14);
				const rb = w * (1 - (k + 1) * 0.14) * (k === 2 ? 0.92 : 1);
				cap(p, q, ra, rb);
				p = q;
				a += o.curl * (0.12 + k * 0.08) * (ang0 < 0 ? 1 : 1);
			}
		}
		// pulgar: nace abajo, a un lado del dorso
		let p: Pt = [-0.19, -0.15];
		let a = -0.72 - 0.3 * sp;
		const tl = [0.18, 0.13, 0.1];
		for (let k = 0; k < 3; k++) {
			const q: Pt = [p[0] + Math.sin(a) * tl[k], p[1] - Math.cos(a) * tl[k]];
			cap(p, q, 0.066 - k * 0.01, 0.056 - k * 0.011);
			p = q;
			a += 0.22 + o.curl * 0.12;
		}
		ctx.restore();
	};
	if (o.rim) {
		draw(o.rim, 0, 0);
		draw(o.fill, -(o.rimPx ?? 2), (o.rimPx ?? 2) * 0.6);
	} else {
		draw(o.fill, 0, 0);
	}
};
