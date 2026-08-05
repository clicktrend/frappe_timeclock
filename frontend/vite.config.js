import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"

// The frappeui plugin derives outDir (../timeclock/public/frontend) and the
// asset base URL (/assets/timeclock/frontend/) from the app layout, proxies
// /api etc. to the local bench in dev, resolves ~icons/lucide/* and copies the
// built index.html to www so Frappe serves the SPA at /kiosk.
export default defineConfig({
	plugins: [
		frappeui({
			lucideIcons: true,
			frappeProxy: true,
			jinjaBootData: true,
			buildConfig: {
				indexHtmlPath: "../timeclock/www/kiosk.html",
			},
		}),
		vue(),
	],
})
