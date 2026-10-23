/**
 * Siluetas humanas procedurales (canvas 2D).
 * Se construye un esqueleto 2D (unidades = altura de la figura, y hacia arriba, origen en los pies)
 * y se rellena con formas suaves (cápsulas cónicas, torso con curvas, cabeza, pelo y ropa).
 */
import {clamp, makeRng} from './rng';

export type View = 'front' | 'side';
export type Hair = 'short' | 'long' | 'bun' | 'curly' | 'hood' | 'cap';
export type Clothing = 'hoodie' | 'jacket' | 'tshirt' | 'dress' | 'coat';

export type Pose = {
	head: number; // + = mirar hacia arriba
	lean: number; // + = inclinarse hacia atrás (vista lateral)
	ls: number; // brazo izq.: ángulo desde abajo (frente: hacia afuera; lateral: hacia delante)
	le: number; // flexión codo izq.
	rs: number;
	re: number;
	lh: number; // pierna izq.: balanceo adelante/atrás (rad)
	lk: number; // flexión rodilla izq.
	rh: number;
	rk: number;
	spread: number; // apertura de piernas (vista frontal)
	bob: number; // desplazamiento vertical (fracción de altura)
	sway: number; // balanceo lateral de cadera (vista frontal)
	armFB: number; // escorzo de brazos (vista frontal, 0 = sin escorzo)
	lsw: number; // balanceo adelante/atrás del brazo izq. (marcha)
	rsw: number;
	hands: 'open' | 'relaxed';
};

export type Style = {
	build: number; // anchura
	hair: Hair;
	clothing: Clothing;
	female: boolean;
	headScale: number;
};

export const basePose = (): Pose => ({
	head: 0,
	lean: 0,
	ls: 0.07,
	le: 0.06,
	rs: 0.07,
	re: 0.06,
	lh: 0,
	lk: 0.04,
	rh: 0,
	rk: 0.04,
	spread: 0.045,
	bob: 0,
	sway: 0,
	armFB: 0,
	lsw: 0,
	rsw: 0,
	hands: 'relaxed',
});

export const randomStyle = (seed: number): Style => {
	const r = makeRng(seed * 7919 + 13);
	const female = r() < 0.5;
	const hairs: Hair[] = female ? ['long', 'long', 'bun', 'curly', 'short', 'hood'] : ['short', 'short', 'curly', 'hood', 'cap', 'short'];
	const clothes: Clothing[] = female ? ['jacket', 'hoodie', 'tshirt', 'dress', 'coat'] : ['hoodie', 'jacket', 'tshirt', 'coat', 'hoodie'];
	return {
		build: (female ? 0.9 : 1.02) + r() * 0.12,
		hair: hairs[Math.floor(r() * hairs.length)],
		clothing: clothes[Math.floor(r() * clothes.length)],
		female,
		headScale: 0.96 + r() * 0.08,
	};
};

/** Ciclo de marcha. phase en radianes. */
export const walkPose = (phase: number, amount = 1): Pose => {
	const s = Math.sin(phase);
	const p = basePose();
	const swing = 0.36 * amount;
	p.lh = swing * s;
	p.rh = -swing * s;
	const knee = (ph: number) => 0.1 + 0.62 * Math.pow(Math.max(0, Math.sin(ph + 1.9)), 1.6) * amount;
	p.lk = knee(phase);
	p.rk = knee(phase + Math.PI);
	p.ls = 0.07;
	p.rs = 0.07;
	p.lsw = -0.34 * s * amount;
	p.rsw = 0.34 * s * amount;
	p.le = 0.22 + 0.18 * Math.max(0, -s) * amount;
	p.re = 0.22 + 0.18 * Math.max(0, s) * amount;
	p.bob = 0.008 * Math.cos(2 * phase) * amount;
	p.sway = 0.008 * s * amount;
	p.spread = 0.025;
	return p;
};

/** Manos levantadas en adoración (t en segundos para un balanceo sutil). */
export const worshipPose = (t: number, seed: number, intensity = 1): Pose => {
	const r = makeRng(seed * 31 + 7);
	const p = basePose();
	const both = r() < 0.72;
	const base = 2.45 + r() * 0.45;
	const sway = Math.sin(t * (0.8 + r() * 0.6) + r() * 6) * 0.08;
	p.rs = (base + sway) * intensity + (1 - intensity) * 0.15;
	p.re = 0.15 + r() * 0.35;
	if (both) {
		p.ls = (base - 0.05 + r() * 0.1 - sway) * intensity + (1 - intensity) * 0.15;
		p.le = 0.15 + r() * 0.35;
	} else {
		p.ls = 0.12 + r() * 0.12;
		p.le = -(1.75 + r() * 0.45);
	}
	p.head = 0.15 + r() * 0.25;
	p.hands = 'open';
	p.armFB = 0.15 + r() * 0.25;
	p.sway = Math.sin(t * 0.7 + seed) * 0.006;
	return p;
};

type Pt = [number, number];

export type DrawOpts = {
	x: number;
	y: number;
	h: number;
	view: View;
	facing?: 1 | -1;
	pose: Pose;
	style: Style;
	fill: string;
};

const rot = (a: number): Pt => [Math.sin(a), -Math.cos(a)];

/** Dibuja la silueta en ctx (relleno opaco). */
export const drawFigure = (ctx: CanvasRenderingContext2D, o: DrawOpts) => {
	const {x, y, h, pose: p, style: s} = o;
	const f = o.facing ?? 1;
	const X = (mx: number) => x + mx * h * (o.view === 'side' ? f : 1);
	const Y = (my: number) => y - my * h;
	ctx.fillStyle = o.fill;

	const circle = (c: Pt, r: number) => {
		ctx.beginPath();
		ctx.arc(X(c[0]), Y(c[1]), Math.max(0.3, r * h), 0, Math.PI * 2);
		ctx.fill();
	};
	const ellipse = (c: Pt, rx: number, ry: number, ang = 0) => {
		ctx.beginPath();
		ctx.ellipse(X(c[0]), Y(c[1]), Math.max(0.3, rx * h), Math.max(0.3, ry * h), ang * (o.view === 'side' ? f : 1), 0, Math.PI * 2);
		ctx.fill();
	};
	const capsule = (a: Pt, b: Pt, ra: number, rb: number) => {
		const ax = X(a[0]);
		const ay = Y(a[1]);
		const bx = X(b[0]);
		const by = Y(b[1]);
		const dx = bx - ax;
		const dy = by - ay;
		const len = Math.hypot(dx, dy) || 1e-6;
		const nx = -dy / len;
		const ny = dx / len;
		ctx.beginPath();
		ctx.moveTo(ax + nx * ra * h, ay + ny * ra * h);
		ctx.lineTo(bx + nx * rb * h, by + ny * rb * h);
		ctx.lineTo(bx - nx * rb * h, by - ny * rb * h);
		ctx.lineTo(ax - nx * ra * h, ay - ny * ra * h);
		ctx.closePath();
		ctx.fill();
		circle(a, ra);
		circle(b, rb);
	};
	const poly = (pts: Pt[], curved = true) => {
		ctx.beginPath();
		const P = pts.map(([px, py]) => [X(px), Y(py)] as Pt);
		if (!curved) {
			ctx.moveTo(P[0][0], P[0][1]);
			for (let i = 1; i < P.length; i++) {
				ctx.lineTo(P[i][0], P[i][1]);
			}
		} else {
			const n = P.length;
			const mid = (i: number): Pt => [(P[i % n][0] + P[(i + 1) % n][0]) / 2, (P[i % n][1] + P[(i + 1) % n][1]) / 2];
			const m0 = mid(n - 1);
			ctx.moveTo(m0[0], m0[1]);
			for (let i = 0; i < n; i++) {
				const m = mid(i);
				ctx.quadraticCurveTo(P[i][0], P[i][1], m[0], m[1]);
			}
		}
		ctx.closePath();
		ctx.fill();
	};

	const b = s.build;
	const bob = p.bob;
	const hs = s.headScale;
	const thick = s.clothing === 'hoodie' || s.clothing === 'coat' ? 1.12 : s.clothing === 'jacket' ? 1.06 : 1.0;

	if (o.view === 'front') {
		const sx = p.sway;
		const hipY = 0.5 + bob;
		const shY = 0.805 + bob;
		const sw = (s.female ? 0.098 : 0.11) * b * (thick > 1.05 ? 1.04 : 1);
		// piernas (muslo cónico, pantorrilla, tobillo, zapato)
		const leg = (side: -1 | 1, swing: number, knee: number) => {
			const hip: Pt = [sx + side * 0.05 * b, hipY + 0.005];
			const sp = p.spread * side;
			const tl = 0.245 * Math.cos(swing);
			const sl = 0.235 * Math.cos(swing - knee);
			const kneeP: Pt = [hip[0] + Math.sin(sp) * tl - side * 0.006, hip[1] - tl];
			const ank: Pt = [kneeP[0] + Math.sin(sp * 0.6) * sl, Math.max(kneeP[1] - sl, 0.045 + bob)];
			const calf: Pt = [kneeP[0] * 0.65 + ank[0] * 0.35 + side * 0.004, kneeP[1] * 0.65 + ank[1] * 0.35];
			const tr = (s.clothing === 'dress' ? 0.036 : 0.052) * b;
			capsule(hip, kneeP, tr, 0.034 * b);
			capsule(kneeP, calf, 0.034 * b, 0.037 * b);
			capsule(calf, ank, 0.037 * b, 0.022 * b);
			ellipse([ank[0] + side * 0.008, ank[1] - 0.026], 0.034 * b, 0.022, 0);
		};
		leg(-1, p.lh, p.lk);
		leg(1, p.rh, p.rk);
		// torso (contorno anatómico, simétrico)
		const waistW = (s.female ? 0.072 : 0.088) * b * thick;
		const hipW = (s.female ? 0.098 : 0.09) * b * (s.clothing === 'hoodie' ? 1.1 : 1);
		const hemY = s.clothing === 'coat' ? 0.3 : s.clothing === 'dress' ? 0.29 : s.clothing === 'hoodie' ? 0.455 : 0.47;
		const hemW = s.clothing === 'dress' ? 0.145 * b : s.clothing === 'coat' ? 0.112 * b : hipW * 1.02;
		const cx = sx * 0.5;
		const neckW = (s.female ? 0.021 : 0.026) * b;
		poly([
			[cx - neckW, shY + 0.05],
			[cx + neckW, shY + 0.05],
			[cx + neckW * 1.4, shY + 0.022],
			[cx + sw * 0.78, shY + 0.008],
			[cx + sw * 1.02, shY - 0.02],
			[cx + sw * 0.98 * thick, shY - 0.075],
			[cx + sw * 0.86 * thick, shY - 0.11],
			[sx * 0.8 + waistW, 0.625 + bob],
			[sx + hipW, hipY + 0.035],
			[sx + hemW, hemY + bob],
			[sx - hemW, hemY + bob],
			[sx - hipW, hipY + 0.035],
			[sx * 0.8 - waistW, 0.625 + bob],
			[cx - sw * 0.86 * thick, shY - 0.11],
			[cx - sw * 0.98 * thick, shY - 0.075],
			[cx - sw * 1.02, shY - 0.02],
			[cx - sw * 0.78, shY + 0.008],
			[cx - neckW * 1.4, shY + 0.022],
		]);
		// brazos
		const arm = (side: -1 | 1, a: number, e: number) => {
			const sh: Pt = [cx + side * (sw * 0.74), shY - 0.04];
			const swing = side === -1 ? p.lsw : p.rsw;
			const fs = Math.cos(p.armFB) * Math.cos(swing);
			const u = rot(a);
			const el: Pt = [sh[0] + side * u[0] * 0.18 * fs, sh[1] + u[1] * 0.18 * fs];
			const v = rot(a + e);
			const wr: Pt = [el[0] + side * v[0] * 0.155 * fs, el[1] + v[1] * 0.155 * fs];
			capsule(sh, el, 0.036 * b * thick, 0.029 * b * thick);
			capsule(el, wr, 0.028 * b * thick, 0.019 * b);
			const ha = a + e * 1.05;
			const hw = rot(ha);
			if (p.hands === 'open') {
				const palmC: Pt = [wr[0] + side * hw[0] * 0.038, wr[1] + hw[1] * 0.038];
				const pr = rot(ha + Math.PI / 2);
				ellipse(palmC, 0.021, 0.031, -ha * side);
				for (let k = 0; k < 4; k++) {
					const off = (k - 1.5) * 0.0105;
					const fa = ha + (k - 1.5) * 0.12 * side;
					const fd = rot(fa);
					const len = [0.042, 0.05, 0.048, 0.038][k];
					const base: Pt = [palmC[0] + side * hw[0] * 0.022 + side * pr[0] * off, palmC[1] + hw[1] * 0.022 + pr[1] * off];
					capsule(base, [base[0] + side * fd[0] * len, base[1] + fd[1] * len], 0.0062, 0.005);
				}
				const ta = ha - 0.9 * side;
				const td = rot(ta);
				const tb: Pt = [palmC[0] - side * pr[0] * 0.018, palmC[1] - pr[1] * 0.018];
				capsule(tb, [tb[0] + side * td[0] * 0.034, tb[1] + td[1] * 0.034], 0.0075, 0.0055);
			} else {
				capsule(wr, [wr[0] + side * hw[0] * 0.075, wr[1] + hw[1] * 0.075], 0.021, 0.017);
			}
		};
		arm(-1, p.ls, p.le);
		arm(1, p.rs, p.re);
		// cabeza ovalada (más ancha arriba, mandíbula estrecha)
		const hc: Pt = [sx * 0.25, 0.925 + bob + p.head * 0.01];
		const hrx = (s.female ? 0.05 : 0.053) * hs;
		const hry = 0.064 * hs;
		ellipse([hc[0], hc[1] + 0.008], hrx, hry * 0.9);
		ellipse([hc[0], hc[1] - 0.022], hrx * 0.78, hry * 0.6);
		// pelo
		if (s.hair === 'short') {
			ellipse([hc[0], hc[1] + 0.02], hrx * 1.04, hry * 0.82);
		} else if (s.hair === 'curly') {
			for (let k = 0; k < 9; k++) {
				const ang = (k / 8) * Math.PI;
				circle([hc[0] + Math.cos(ang) * hrx * 0.95, hc[1] + 0.012 + Math.sin(ang) * hry * 0.95], 0.022 * hs);
			}
		} else if (s.hair === 'long') {
			poly([
				[hc[0] - hrx * 1.1, hc[1] + 0.01],
				[hc[0], hc[1] + hry * 1.12],
				[hc[0] + hrx * 1.1, hc[1] + 0.01],
				[hc[0] + hrx * 1.2, hc[1] - 0.07],
				[hc[0] + hrx * 1.0, shY - 0.05],
				[hc[0] - hrx * 1.0, shY - 0.05],
				[hc[0] - hrx * 1.2, hc[1] - 0.07],
			]);
		} else if (s.hair === 'bun') {
			ellipse([hc[0], hc[1] + 0.018], hrx * 1.04, hry * 0.84);
			circle([hc[0], hc[1] + hry * 1.12], 0.027 * hs);
		} else if (s.hair === 'hood') {
			ellipse([hc[0], hc[1] + 0.005], hrx * 1.32, hry * 1.18);
			ellipse([hc[0], shY + 0.03], 0.075, 0.035);
		} else if (s.hair === 'cap') {
			ellipse([hc[0], hc[1] + 0.03], hrx * 1.08, hry * 0.62);
			ellipse([hc[0], hc[1] + 0.016], hrx * 1.35, hry * 0.16);
		}
		return;
	}

	// ------------------------------------------------------------- vista lateral
	const hipP: Pt = [0, 0.5 + bob];
	const lean = p.lean;
	const up = (len: number, extra = 0): Pt => [hipP[0] + Math.sin(-lean + extra) * len, hipP[1] + Math.cos(-lean + extra) * len];
	const shP = up(0.3, 0.06);
	const legS = (swing: number, knee: number, far: boolean) => {
		const tl = 0.245;
		const sl = 0.24;
		const u = rot(Math.PI + 0) as Pt;
		void u;
		const kneeP: Pt = [hipP[0] + Math.sin(swing) * tl, hipP[1] - Math.cos(swing) * tl];
		const sa = swing - knee;
		const ank: Pt = [kneeP[0] + Math.sin(sa) * sl, kneeP[1] - Math.cos(sa) * sl];
		const tr = (s.clothing === 'dress' ? 0.034 : 0.05) * b * (far ? 0.95 : 1);
		capsule([hipP[0] - 0.005, hipP[1]], kneeP, tr, 0.036 * b);
		capsule(kneeP, ank, 0.035 * b, 0.026 * b);
		// pie
		const toe: Pt = [ank[0] + Math.cos(sa) * 0.1, ank[1] + Math.sin(sa) * 0.1 * 0.3 - 0.018];
		capsule([ank[0] - 0.015, ank[1] - 0.018], toe, 0.02, 0.014);
	};
	legS(p.rh, p.rk, true);
	legS(p.lh, p.lk, false);
	// torso de perfil
	const chestF = (s.female ? 0.07 : 0.072) * b * thick;
	const backB = 0.06 * b * thick;
	const hem = s.clothing === 'coat' || s.clothing === 'dress' ? 0.3 : 0.47;
	const L = (len: number, side: number): Pt => {
		const c = up(len);
		const nx = Math.cos(-lean);
		const ny = -Math.sin(-lean);
		return [c[0] + nx * side, c[1] + ny * side];
	};
	poly([
		L(0.31, 0.03),
		L(0.27, chestF),
		L(0.18, chestF * 0.9),
		L(0.1, chestF * 0.85),
		L(0.02, chestF * 0.95),
		[hipP[0] + (s.clothing === 'dress' ? 0.12 : 0.06) * b, hem + bob],
		[hipP[0] - (s.clothing === 'dress' ? 0.1 : 0.065) * b, hem + bob],
		L(0.02, -backB * 1.05),
		L(0.12, -backB * 0.85),
		L(0.25, -backB),
		L(0.31, -0.035),
	]);
	// cabeza
	const neck = up(0.34, 0.08);
	const hc: Pt = [neck[0] + Math.sin(-lean * 0.5 - p.head * 0.4) * 0.07 + 0.008, neck[1] + 0.07];
	capsule(up(0.3, 0.05), neck, 0.034 * b, 0.03 * b);
	const fa = -p.head * 0.8;
	ellipse(hc, 0.058 * hs, 0.06 * hs, fa);
	// mandíbula y nariz (perfil)
	const jaw: Pt = [hc[0] + Math.cos(fa - 0.9) * 0.035, hc[1] + Math.sin(fa - 0.9) * 0.045];
	ellipse(jaw, 0.034 * hs, 0.026 * hs, fa - 0.4);
	const nose: Pt = [hc[0] + Math.cos(fa - 0.1) * 0.058 * hs, hc[1] + Math.sin(fa - 0.1) * 0.058 * hs - 0.004];
	ellipse(nose, 0.011, 0.007, fa);
	if (s.hair === 'long') {
		poly([
			[hc[0] + 0.02, hc[1] + 0.07],
			[hc[0] - 0.062, hc[1] + 0.03],
			[hc[0] - 0.07, hc[1] - 0.09],
			[hc[0] - 0.02, hc[1] - 0.1],
			[hc[0] - 0.01, hc[1] - 0.02],
		]);
	} else if (s.hair === 'bun') {
		circle([hc[0] - 0.05, hc[1] + 0.045], 0.03);
	} else if (s.hair === 'hood') {
		ellipse([hc[0] - 0.015, hc[1] + 0.005], 0.07, 0.075, fa);
	} else if (s.hair === 'curly') {
		for (let k = 0; k < 7; k++) {
			const ang = Math.PI * (0.25 + k * 0.13);
			circle([hc[0] + Math.cos(ang) * 0.05, hc[1] + 0.01 + Math.sin(ang) * 0.05], 0.022);
		}
	} else {
		ellipse([hc[0] - 0.008, hc[1] + 0.014], 0.058 * hs, 0.058 * hs, fa);
	}
	// brazo (el lejano primero ya queda tapado por el torso)
	const armS = (a: number, e: number) => {
		const sh: Pt = [shP[0] - 0.01, shP[1] - 0.02];
		const u = rot(a);
		const el: Pt = [sh[0] + u[0] * 0.175, sh[1] + u[1] * 0.175];
		const v = rot(a + e);
		const wr: Pt = [el[0] + v[0] * 0.155, el[1] + v[1] * 0.155];
		capsule(sh, el, 0.036 * b * thick, 0.028 * b * thick);
		capsule(el, wr, 0.027 * b * thick, 0.02 * b);
		const hw = rot(a + e * 1.15);
		capsule(wr, [wr[0] + hw[0] * 0.075, wr[1] + hw[1] * 0.075], 0.02, 0.015);
	};
	armS(p.rsw !== 0 ? p.rsw : p.rs, p.re);
	armS(p.lsw !== 0 ? p.lsw : p.ls, p.le);
};

/** Dibuja una figura con halo de contraluz y borde iluminado. */
export const drawLitFigure = (
	ctx: CanvasRenderingContext2D,
	o: DrawOpts & {rim?: string; rimPx?: number; rimDir?: [number, number]},
) => {
	if (o.rim) {
		const d = o.rimDir ?? [0.6, -0.8];
		const px = o.rimPx ?? Math.max(1, o.h * 0.006);
		drawFigure(ctx, {...o, fill: o.rim});
		drawFigure(ctx, {...o, x: o.x - d[0] * px, y: o.y - d[1] * px * 0.6 + px * 0.25, fill: o.fill});
	} else {
		drawFigure(ctx, o);
	}
};

export const lerpPose = (a: Pose, b: Pose, t: number): Pose => {
	const k = clamp(t);
	const out = {...a};
	(Object.keys(a) as (keyof Pose)[]).forEach((key) => {
		if (typeof a[key] === 'number') {
			(out as Record<string, unknown>)[key] = (a[key] as number) * (1 - k) + (b[key] as number) * k;
		}
	});
	out.hands = k > 0.5 ? b.hands : a.hands;
	return out;
};
