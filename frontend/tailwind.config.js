import frappeUIPreset from "frappe-ui/tailwind"
import colors from "tailwindcss/colors"

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js}",
	],
	theme: {
		extend: {
			// The frappe-ui preset REPLACES the tailwind palette (gray/blue/green/... only).
			// The kiosk dark theme needs zinc surfaces and emerald accents — bring them back.
			colors: {
				zinc: colors.zinc,
				emerald: colors.emerald,
			},
		},
	},
}
