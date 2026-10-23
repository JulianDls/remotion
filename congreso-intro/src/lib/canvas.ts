/** Prepara un canvas a la resolución real del render (soporta --scale para 4K). */
export const dpr = () => (typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1);

export const prep = (c: HTMLCanvasElement, w: number, h: number) => {
	const r = dpr();
	const bw = Math.round(w * r);
	const bh = Math.round(h * r);
	if (c.width !== bw || c.height !== bh) {
		c.width = bw;
		c.height = bh;
	}
	const ctx = c.getContext('2d')!;
	ctx.setTransform(r, 0, 0, r, 0, 0);
	ctx.clearRect(0, 0, w, h);
	return ctx;
};
