/** Generador pseudoaleatorio determinista (mulberry32). */
export const makeRng = (seed: number) => {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
};

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const smooth = (t: number) => {
	const x = clamp(t);
	return x * x * (3 - 2 * x);
};
export const easeInOut = (t: number) => {
	const x = clamp(t);
	return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
};
export const easeOut = (t: number) => 1 - Math.pow(1 - clamp(t), 3);
export const easeIn = (t: number) => Math.pow(clamp(t), 3);

/** Ruido 1D suave (valor) para movimientos orgánicos. */
export const noise1 = (x: number, seed = 0) => {
	const h = (n: number) => {
		const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
		return s - Math.floor(s);
	};
	const i = Math.floor(x);
	const f = x - i;
	const u = f * f * (3 - 2 * f);
	return lerp(h(i), h(i + 1), u) * 2 - 1;
};
