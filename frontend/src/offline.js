// Offline support for the kiosk: what survives on the device while the server
// cannot be reached, and how it gets there.
//
// The device stores punches, never the means to verify them: PIN and badge travel
// inside the queued punch and the server checks them at sync time
// (timeclock/offline.py). The only badge data kept here is a SHA-256 hash, enough
// to put a name on the confirmation screen.
//
// localStorage instead of IndexedDB on purpose: a few hundred small entries at
// most, synchronous (no punch is lost between "saved" on screen and the write),
// and every access is wrapped — a private window or a full disk must surface as
// "could not save", never as a silent loss.

const KEYS = {
	queue: "timeclock.queue.v1",
	employees: "timeclock.employees.v1",
	config: "timeclock.config.v1",
	clock: "timeclock.clock.v1",
}

function load(key, fallback) {
	try {
		const raw = window.localStorage.getItem(key)
		return raw ? JSON.parse(raw) : fallback
	} catch {
		return fallback
	}
}

function save(key, value) {
	try {
		window.localStorage.setItem(key, JSON.stringify(value))
		return true
	} catch {
		return false
	}
}

export const loadQueue = () => load(KEYS.queue, [])
export const saveQueue = (queue) => save(KEYS.queue, queue)
export const loadEmployees = () => load(KEYS.employees, null)
export const saveEmployees = (employees) => save(KEYS.employees, employees)
export const loadConfig = () => load(KEYS.config, null)
export const saveConfig = (config) => save(KEYS.config, config)
// { offset: ms the server wall clock is ahead of the tablet, at: wall time of the measurement }
export const loadClock = () => load(KEYS.clock, null)
export const saveClock = (clock) => save(KEYS.clock, clock)

// Hash part of the bundle's own file name (index-<hash>.js). The server reads the
// same value from the page it ships, so an outdated kiosk is recognised without
// any build step injecting a version.
export const BUILD = (import.meta.url.match(/index-([\w-]+)\.js/) || [])[1] || "dev"

export function newPunchId() {
	if (window.crypto?.randomUUID) return window.crypto.randomUUID().replaceAll("-", "")
	return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("")
}

// Badge IDs are issued as 32 hex characters (uuid4().hex). Anything else held into
// the camera — a parcel label, a Marello QR — is not worth queuing.
export const looksLikeBadge = (code) => /^[0-9a-f]{32}$/i.test(String(code || "").trim())

// crypto.subtle only exists in a secure context (HTTPS, localhost) — without it the
// badge is still queued, just without a name on the screen.
export async function sha256Hex(text) {
	if (!window.crypto?.subtle) return null
	const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text.trim()))
	return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("")
}

// "YYYY-MM-DD HH:mm:ss" from local getters — fed with Date.now() + clockOffset this
// is site wall time, exactly like the clock on the screen.
export function wallTime(ms) {
	const d = new Date(ms)
	const pad = (n) => String(n).padStart(2, "0")
	return (
		`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
		`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
	)
}

export function registerServiceWorker() {
	if (import.meta.env.DEV || !("serviceWorker" in navigator) || !window.isSecureContext) return
	const precache = () => {
		const urls = performance
			.getEntriesByType("resource")
			.map((entry) => entry.name)
			.filter((name) => new URL(name, location.origin).pathname.startsWith("/assets/"))
		navigator.serviceWorker.ready.then((reg) => reg.active?.postMessage({ type: "precache", urls }))
	}
	navigator.serviceWorker
		.register("/kiosk-sw.js", { scope: "/kiosk" })
		.then(() => {
			precache()
			// the QR scanner loads its worker chunk lazily — catch that one too
			setTimeout(precache, 30_000)
		})
		.catch(() => {
			// no worker means no cold start offline; punching offline still works
		})
}
