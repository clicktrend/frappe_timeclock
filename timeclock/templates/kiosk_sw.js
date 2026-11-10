// Timeclock kiosk service worker, served at /kiosk-sw.js (timeclock/kiosk_sw.py).
//
// Its only job: the kiosk page must start even when the tablet reboots while the
// server is unreachable. Everything else about offline punching lives in the page
// itself (frontend/src/offline.js). The worker never touches /api — punches are
// queued by the page, not by the worker.
const CACHE = "timeclock-kiosk-v1"
const PAGE_KEY = "/kiosk"
const BUNDLE_PREFIX = "/assets/timeclock/frontend/"

self.addEventListener("install", () => self.skipWaiting())
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()))

self.addEventListener("fetch", (event) => {
	const request = event.request
	if (request.method !== "GET") return
	const url = new URL(request.url)
	if (url.origin !== self.location.origin) return

	if (request.mode === "navigate" && url.pathname === PAGE_KEY) {
		event.respondWith(page(request))
	} else if (url.pathname.startsWith(BUNDLE_PREFIX)) {
		event.respondWith(bundleAsset(url.pathname))
	} else if (url.pathname.startsWith("/assets/")) {
		event.respondWith(otherAsset(request, url.pathname))
	}
})

// The page asks for its own resources to be kept, once it runs (the first load
// happens before the worker controls anything, so nothing was cached yet).
self.addEventListener("message", (event) => {
	if (event.data?.type === "precache") event.waitUntil(precache(event.data.urls || []))
})

// Network first: a reachable server always wins, so a new build arrives as soon
// as it is deployed. The cached copy is only for "no answer" or a proxy error
// page — never for a redirect to /login, which the kiosk must follow.
async function page(request) {
	const cache = await caches.open(CACHE)
	try {
		const response = await fetch(request)
		if (response.ok && !response.redirected) {
			cache.put(PAGE_KEY, response.clone())
			return response
		}
		if (response.redirected) return response
		return (await cache.match(PAGE_KEY)) || response
	} catch {
		return (await cache.match(PAGE_KEY)) || Response.error()
	}
}

// Bundle files carry a content hash in their name — cache first is safe.
async function bundleAsset(path) {
	const cache = await caches.open(CACHE)
	const hit = await cache.match(path)
	if (hit) return hit
	const response = await fetch(path)
	if (response.ok) cache.put(path, response.clone())
	return response
}

async function otherAsset(request, path) {
	const cache = await caches.open(CACHE)
	try {
		const response = await fetch(request)
		if (response.ok) cache.put(path, response.clone())
		return response
	} catch {
		return (await cache.match(path)) || Response.error()
	}
}

async function precache(urls) {
	const cache = await caches.open(CACHE)
	try {
		const response = await fetch(PAGE_KEY, { credentials: "same-origin" })
		if (response.ok && !response.redirected) await cache.put(PAGE_KEY, response)
	} catch {
		// offline right now — the next page load tries again
	}

	const keep = new Set()
	for (const raw of urls) {
		const url = new URL(raw, self.location.origin)
		if (url.origin !== self.location.origin || !url.pathname.startsWith("/assets/")) continue
		keep.add(url.pathname)
		if (await cache.match(url.pathname)) continue
		try {
			const response = await fetch(url.pathname)
			if (response.ok) await cache.put(url.pathname, response)
		} catch {
			// same as above
		}
	}

	// drop the bundle files of earlier builds
	if (!keep.size) return
	for (const request of await cache.keys()) {
		const path = new URL(request.url).pathname
		if (path.startsWith(BUNDLE_PREFIX) && !keep.has(path)) await cache.delete(request)
	}
}
