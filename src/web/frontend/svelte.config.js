import adapter from '@sveltejs/adapter-vercel';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// Hosted on Vercel (its own project, root src/web/frontend). `npm run dev`
		// is unaffected; the adapter only shapes `npm run build`.
		adapter: adapter({ runtime: 'nodejs20.x' })
	}
};

export default config;
