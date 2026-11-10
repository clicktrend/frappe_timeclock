<template>
	<div class="flex h-screen flex-col bg-[#0f1115] text-zinc-100">
		<!-- Screen: home — clock-first idle like commercial terminals, badge scan active -->
		<main v-if="screen === 'home'" class="flex flex-1 flex-col items-center justify-center gap-2 p-6">
			<div class="font-mono text-[7rem] font-semibold leading-none tracking-tight sm:text-[9rem]">
				{{ clock }}
			</div>
			<div class="text-2xl text-zinc-400">{{ today }}</div>

			<!-- Offline mode: punching continues, the device keeps the punches -->
			<div
				v-if="offline && canPunchOffline"
				class="mt-8 rounded-2xl bg-amber-500/15 px-6 py-3 text-center ring-1 ring-amber-500/30"
			>
				<div class="text-lg font-semibold text-amber-300">{{ t("offline_mode_title") }}</div>
				<div class="text-sm text-amber-200/80">{{ t("offline_mode_hint") }}</div>
			</div>
			<div v-if="queue.length" class="mt-3 text-sm text-zinc-400">
				{{ t("queue_waiting").replace("{n}", queue.length) }}
			</div>

			<!-- Badge prompt / scanner state -->
			<div class="mt-12 flex flex-col items-center gap-3">
				<template v-if="offline && !canPunchOffline">
					<div class="text-6xl" aria-hidden="true">⚠️</div>
					<div class="text-xl font-semibold text-amber-400">{{ t("offline_title") }}</div>
					<div class="text-sm text-zinc-500">{{ t("offline_hint") }}</div>
				</template>
				<template v-else-if="camAvailable">
					<div class="relative flex h-24 w-24 items-center justify-center">
						<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500/20"></span>
						<span class="relative flex h-20 w-20 items-center justify-center rounded-full bg-zinc-900 text-5xl ring-1 ring-zinc-700">🪪</span>
					</div>
					<div class="text-xl font-medium text-zinc-200">{{ t("badge_prompt") }}</div>
					<div v-if="scanError" class="text-lg font-medium text-red-400">{{ scanError }}</div>
					<div v-else-if="scanBusy" class="text-base text-zinc-400">{{ t("scanning") }}</div>
					<div v-else class="flex items-center gap-2 text-sm text-zinc-500">
						<span class="relative flex h-2 w-2">
							<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
							<span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
						</span>
						{{ t("scanner_ready") }}
					</div>
				</template>
				<template v-else>
					<div class="text-6xl" aria-hidden="true">⚠️</div>
					<div class="text-xl font-semibold text-amber-400">{{ t("scanner_down_title") }}</div>
					<div class="text-sm text-zinc-500">{{ t("scanner_down_hint") }}</div>
				</template>
			</div>

			<button
				class="mt-12 rounded-2xl px-10 py-5 text-xl font-medium shadow-lg transition active:scale-95 disabled:opacity-40 disabled:active:scale-100"
				:class="camAvailable ? 'bg-zinc-900 text-zinc-200 ring-1 ring-zinc-700' : 'bg-blue-600 text-white'"
				:disabled="offline && !canPunchOffline"
				@click="screen = 'grid'"
			>
				{{ t("without_badge") }}
			</button>

			<!-- hidden (or preview) camera element — must stay rendered for frame grabbing -->
			<video ref="videoEl" :class="videoClass"></video>
		</main>

		<!-- Screen: employee grid (PIN path), scanner stays active -->
		<main v-else-if="screen === 'grid'" class="flex min-h-0 flex-1 flex-col">
			<header class="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
				<button class="flex items-center gap-2 rounded-xl px-4 py-2 text-lg text-zinc-300 transition active:scale-95 active:bg-zinc-800" @click="reset">
					<span class="text-2xl leading-none">‹</span> {{ t("back") }}
				</button>
				<div class="text-lg font-medium text-zinc-400">{{ t("choose_employee") }}</div>
				<div class="font-mono text-2xl text-zinc-300">{{ clock }}</div>
			</header>

			<div class="min-h-0 flex-1 overflow-y-auto p-6">
				<div v-if="!gridEmployees && employees.loading" class="mt-20 text-center text-lg text-zinc-400">
					{{ t("loading_employees") }}
				</div>
				<div v-else-if="!gridEmployees" class="mt-20 text-center text-lg text-red-400">
					{{ t("connection_error") }}<br />
					<span class="text-sm text-zinc-500">{{ t("connection_hint") }}</span>
				</div>
				<div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
					<button
						v-for="emp in gridEmployees"
						:key="emp.name"
						class="flex h-36 flex-col items-center justify-center gap-2 rounded-2xl bg-zinc-900 ring-1 ring-zinc-800 transition active:scale-95 active:bg-zinc-800"
						@click="selectEmployee(emp)"
					>
						<span class="relative">
							<span
								class="flex h-12 w-12 items-center justify-center rounded-full text-base font-semibold text-white"
								:class="avatarColor(emp.employee_name)"
							>
								{{ initials(emp.employee_name) }}
							</span>
							<span
								v-if="emp.last_log_type === 'IN'"
								class="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-emerald-500 ring-2 ring-zinc-900"
							></span>
						</span>
						<span class="px-2 text-center text-base font-medium leading-tight text-zinc-100">{{ emp.employee_name }}</span>
						<span v-if="emp.last_log_type === 'IN'" class="text-xs text-emerald-400">{{ t("since") }} {{ sinceLabel(emp.last_time) }}</span>
						<span v-else class="text-xs text-transparent">·</span>
					</button>
				</div>
			</div>

			<div v-if="scanError" class="border-t border-zinc-800 px-6 py-3 text-center text-base font-medium text-red-400">
				{{ scanError }}
			</div>

			<video ref="videoEl" :class="videoClass"></video>
		</main>

		<!-- Screen: direction + PIN -->
		<main v-else-if="screen === 'pin'" class="flex flex-1 flex-col items-center justify-center gap-6 p-6">
			<div class="flex items-center gap-4">
				<span
					class="flex h-14 w-14 items-center justify-center rounded-full text-lg font-semibold text-white"
					:class="avatarColor(selected.employee_name)"
				>
					{{ initials(selected.employee_name) }}
				</span>
				<div class="text-2xl font-semibold">{{ selected.employee_name }}</div>
			</div>

			<div class="flex gap-4">
				<button
					v-for="dir in ['IN', 'OUT']"
					:key="dir"
					class="flex items-center gap-3 rounded-2xl px-10 py-5 text-xl font-semibold transition active:scale-95"
					:class="
						direction === dir
							? dir === 'IN'
								? 'bg-emerald-600 text-white shadow-lg'
								: 'bg-orange-500 text-white shadow-lg'
							: 'bg-zinc-900 text-zinc-300 ring-1 ring-zinc-700'
					"
					@click="direction = dir"
				>
					<span aria-hidden="true">{{ dir === "IN" ? "➜" : "⬅" }}</span>
					{{ dir === "IN" ? t("clock_in") : t("clock_out") }}
				</button>
			</div>

			<!-- PIN display -->
			<div class="flex h-10 items-center gap-3">
				<span
					v-for="i in 6"
					:key="i"
					class="h-4 w-4 rounded-full border-2 border-zinc-600"
					:class="{ 'border-zinc-100 bg-zinc-100': pin.length >= i }"
				/>
			</div>
			<div v-if="error" class="text-lg font-medium text-red-400">{{ error }}</div>

			<!-- PIN pad -->
			<div class="grid grid-cols-3 gap-3">
				<button
					v-for="key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', 'OK']"
					:key="key"
					class="h-20 w-24 rounded-2xl text-2xl font-semibold transition active:scale-95"
					:class="
						key === 'OK'
							? 'bg-blue-600 text-white disabled:opacity-40'
							: key === 'C'
								? 'bg-zinc-800 text-zinc-300'
								: 'bg-zinc-900 text-zinc-100 ring-1 ring-zinc-800'
					"
					:disabled="key === 'OK' && (pin.length < 4 || punching)"
					@click="pressKey(key)"
				>
					{{ key }}
				</button>
			</div>

			<button class="mt-2 text-lg text-zinc-500 underline" @click="reset">{{ t("cancel") }}</button>
		</main>

		<!-- Screen: confirmation (+ undo window) — name, action, big time -->
		<main
			v-else
			class="flex flex-1 flex-col items-center justify-center gap-3"
			:class="result.log_type === 'IN' ? 'bg-emerald-600' : result.log_type === 'OUT' ? 'bg-orange-500' : 'bg-zinc-700'"
		>
			<!-- explicit rem sizes: the frappe-ui preset shrinks the named text-* scale,
			     but this screen must be readable from across the room -->
			<div class="confirm-pop text-[5.5rem] leading-none text-white">✓</div>
			<div class="text-[1.75rem] font-medium text-white/90">{{ result.employee_name || t("badge_pending") }}</div>
			<div class="text-[3.25rem] font-bold leading-tight text-white">
				{{ result.log_type === "IN" ? t("came") : result.log_type === "OUT" ? t("left") : t("punch_queued") }}
			</div>
			<div class="mt-2 font-mono text-[4.5rem] font-semibold leading-none text-white">
				{{ formatTime(result.time) }}{{ t("time_suffix") }}
			</div>
			<div v-if="result.offline" class="mt-3 rounded-xl bg-black/25 px-5 py-2 text-[1.2rem] font-medium text-white">
				{{ t("saved_offline") }}
			</div>
			<div v-else class="mt-2 text-[1.1rem] text-white/80">{{ t("saved") }}</div>
			<button
				v-if="undoLeft > 0"
				class="mt-8 rounded-2xl bg-white/20 px-10 py-4 text-[1.4rem] font-medium text-white transition active:scale-95"
				@click="doUndo"
			>
				{{ t("undo") }} ({{ undoLeft }})
			</button>
			<div v-if="undoDone" class="text-[1.2rem] text-white/90">{{ t("undone") }}</div>
		</main>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import QrScanner from "qr-scanner"
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"

import { LOCALES, MESSAGES } from "./i18n.js"
import {
	BUILD,
	loadClock,
	loadConfig,
	loadEmployees,
	loadQueue,
	looksLikeBadge,
	newPunchId,
	saveClock,
	saveConfig,
	saveEmployees,
	saveQueue,
	sha256Hex,
	wallTime,
} from "./offline.js"
import { playPunchSound, unlockSound } from "./sound.js"

const DEVICE_ID = new URLSearchParams(window.location.search).get("device") || "kiosk"
const CONFIRM_SECONDS = 5
const SCAN_COOLDOWN_MS = 4000
const IDLE_BACK_MS = 45_000
const HEARTBEAT_MS = 30_000
const SYNC_BATCH = 50

const screen = ref("home")
const selected = ref(null)
const direction = ref("IN")
const pin = ref("")
const error = ref("")
const punching = ref(false)
const result = ref(null)
const undoLeft = ref(0)
const undoDone = ref(false)

const employees = createResource({ url: "timeclock.api.get_kiosk_employees" })
// GET on purpose: after a cold start from the offline cache the page holds a stale
// CSRF token — this request needs none and hands out a fresh one (see the watch below)
const kioskConfig = createResource({ url: "timeclock.api.get_kiosk_config", method: "GET" })
// the last config and grid that worked — what an offline kiosk runs on
const cachedConfig = ref(loadConfig())
const cachedEmployees = ref(loadEmployees())
const config = computed(() => kioskConfig.data || cachedConfig.value)
const showPreview = computed(() => Boolean(config.value?.show_camera_preview))
const soundsEnabled = computed(() => Boolean(config.value?.play_sounds))

const lang = computed(() => (config.value?.language === "en" ? "en" : "de"))
const locale = computed(() => LOCALES[lang.value])
const t = (key) => MESSAGES[lang.value]?.[key] ?? MESSAGES.de[key] ?? key

// The displayed clock is coupled to the SERVER clock (punch timestamps are
// server-side — the display must never disagree with what gets recorded).
// server_time is site-timezone wall time; parsing it as local makes the kiosk
// show site time even if the tablet's clock or timezone is misconfigured.
// The offset is persisted: an offline punch is stamped with tablet time + the last
// known offset, and the server only trusts it if the offset was ever measured.
const storedClock = loadClock()
let clockOffset = storedClock?.offset || 0
const clockSyncedAt = ref(storedClock?.at || null)

function applyServerTime(raw) {
	raw = String(raw || "")
	const parsed = Date.parse(raw.split(".")[0].replace(" ", "T"))
	if (Number.isNaN(parsed)) return
	clockOffset = parsed - Date.now()
	clockSyncedAt.value = raw
	saveClock({ offset: clockOffset, at: raw })
	tick()
}

// version as of page load — config refreshes hourly and would report the server's
// version even while this page still runs the old bundle
let pageVersion = cachedConfig.value?.version || null
watch(
	() => kioskConfig.data,
	(data) => {
		if (!data) return
		if (data.csrf_token) window.csrf_token = data.csrf_token
		if (!pageVersion) pageVersion = data.version
		const { csrf_token, ...stored } = data
		cachedConfig.value = stored
		saveConfig(stored)
		applyServerTime(data.server_time)
	}
)
watch(
	() => employees.data,
	(data) => {
		if (!Array.isArray(data)) return
		cachedEmployees.value = data
		saveEmployees(data)
	}
)

const punch = createResource({ url: "timeclock.api.punch" })
const punchBadge = createResource({ url: "timeclock.api.punch_badge" })
const undoPunch = createResource({ url: "timeclock.api.undo_punch" })
const syncPunches = createResource({ url: "timeclock.api.sync_offline_punches" })
const heartbeatResource = createResource({ url: "timeclock.api.heartbeat" })

// ---- offline queue ----

const queue = ref(loadQueue())
const canPunchOffline = computed(() => Boolean(config.value?.offline_enabled && cachedEmployees.value?.length))

// The grid as the kiosk knows it: last server state plus what is still queued here,
// so the direction suggestion and the green dot stay right while offline.
const gridEmployees = computed(() => {
	const base = employees.data || cachedEmployees.value
	if (!base) return null
	if (!queue.value.length) return base
	const latest = {}
	for (const punch of queue.value) if (punch.employee && punch.log_type) latest[punch.employee] = punch
	return base.map((emp) => {
		const punch = latest[emp.name]
		if (!punch || (emp.last_time && String(emp.last_time) > punch.claimed_time)) return emp
		return {
			...emp,
			last_log_type: punch.log_type,
			last_time: punch.claimed_time,
			suggested_log_type: punch.log_type === "IN" ? "OUT" : "IN",
		}
	})
})

function setQueue(next) {
	if (!saveQueue(next)) return false
	queue.value = next
	return true
}

// Throws a kiosk error with a readable message if the device cannot store it — the
// screen must never say "saved" for a punch that is not.
function enqueue(entry) {
	const now = Date.now()
	const punch = {
		client_uuid: newPunchId(),
		claimed_time: wallTime(now + clockOffset),
		device_time: wallTime(now),
		clock_offset_ms: Math.round(clockOffset),
		clock_synced_at: clockSyncedAt.value,
		...entry,
	}
	if (!setQueue([...queue.value, punch])) throw kioskError(t("offline_save_failed"))
	return {
		offline: true,
		client_uuid: punch.client_uuid,
		employee_name: entry.employee_name,
		log_type: entry.log_type,
		time: punch.claimed_time,
	}
}

function enqueuePin() {
	return enqueue({
		method: "PIN",
		employee: selected.value.name,
		employee_name: selected.value.employee_name,
		pin: pin.value,
		log_type: direction.value,
	})
}

async function enqueueBadge(code) {
	if (!looksLikeBadge(code)) throw kioskError(t("unknown_badge_offline"))
	const hash = await sha256Hex(code)
	const emp = hash && gridEmployees.value?.find((e) => e.badge_hash === hash)
	// an unknown but badge-shaped code is queued too: the server decides, and a
	// rejected one leaves a trace in quarantine instead of vanishing
	return enqueue({
		method: "Badge",
		badge_id: code.trim(),
		employee: emp?.name || null,
		employee_name: emp?.employee_name || null,
		log_type: emp ? emp.suggested_log_type || "IN" : null,
	})
}

let syncing = false
async function syncQueue() {
	if (syncing || offline.value || !queue.value.length) return
	syncing = true
	try {
		const batch = queue.value.slice(0, SYNC_BATCH)
		const results = await syncPunches.submit({ device_id: DEVICE_ID, punches: batch })
		// booked or held in quarantine: either way the server owns it now. "Error"
		// stays on the device and goes out again with the next sync.
		const done = new Set((results || []).filter((r) => r.status !== "Error").map((r) => r.client_uuid))
		setQueue(queue.value.filter((punch) => !done.has(punch.client_uuid)))
		if (done.size) refresh(employees)
		if (done.size && queue.value.length) setTimeout(syncQueue, 0)
	} catch (err) {
		if (isTransportError(err)) goOffline()
	} finally {
		syncing = false
	}
}

async function sendHeartbeat() {
	if (offline.value) return
	try {
		const reply = await heartbeatResource.submit({
			device_id: DEVICE_ID,
			version: pageVersion,
			build: BUILD,
			pending: queue.value.length,
		})
		applyServerTime(reply?.server_time)
		if (queue.value.length) await syncQueue()
		// FreeKiosk never reloads by itself — pick up a new build while nobody is punching
		if (reply?.reload && screen.value === "home" && !queue.value.length) window.location.reload()
	} catch (err) {
		if (isTransportError(err)) goOffline()
	}
}

// ---- V1: grid + PIN ----

function selectEmployee(emp) {
	selected.value = emp
	direction.value = emp.suggested_log_type || "IN"
	pin.value = ""
	error.value = ""
	screen.value = "pin"
}

function pressKey(key) {
	error.value = ""
	if (key === "C") {
		pin.value = ""
	} else if (key === "OK") {
		submit()
	} else if (pin.value.length < 6) {
		pin.value += key
	}
}

async function submit() {
	punching.value = true
	try {
		if (offline.value) {
			showResult(enqueuePin())
			return
		}
		showResult(
			await punch.submit({
				employee: selected.value.name,
				log_type: direction.value,
				pin: pin.value,
				device_id: DEVICE_ID,
			})
		)
	} catch (err) {
		// the connection dropped right now: keep the punch instead of losing it
		if (isTransportError(err) && !err?.isKioskError && canPunchOffline.value) {
			goOffline()
			try {
				showResult(enqueuePin())
				return
			} catch (saveErr) {
				err = saveErr
			}
		}
		error.value = offlineMessage(err) || noteError(err)
		pin.value = ""
	} finally {
		punching.value = false
	}
}

// ---- V2: badge camera ----
// Privacy default: the camera scans WITHOUT showing its image (nobody should feel
// filmed) — the video element stays rendered at 1x1px/opacity-0 so frame grabbing
// keeps working. Admins can opt into a live preview via Timeclock Settings.

const videoEl = ref(null)
const camAvailable = ref(true)
const scanBusy = ref(false)
const scanError = ref("")
let scanner = null
let lastScanCode = ""
let lastScanAt = 0
let scanErrorTimer = null

const videoClass = computed(() =>
	showPreview.value && camAvailable.value
		? "fixed bottom-4 right-4 h-40 w-40 rounded-xl bg-black object-cover ring-1 ring-zinc-700"
		: "pointer-events-none fixed h-px w-px opacity-0"
)

async function startScanner() {
	await nextTick()
	if (!videoEl.value || scanner) return
	try {
		scanner = new QrScanner(videoEl.value, onScan, {
			returnDetailedScanResult: true,
			// wall terminal: badges are held towards the SCREEN, so use the front
			// camera (qr-scanner defaults to the back camera, 'environment')
			preferredCamera: "user",
			maxScansPerSecond: 10,
			// Default scan region is a centered square of 2/3 the frame, downscaled to
			// 400px — badges held slightly off-center are simply not seen. Scan the full
			// frame instead, downscaled proportionally to ~800px on the long edge.
			calculateScanRegion: (video) => {
				const scale = Math.min(1, 800 / Math.max(video.videoWidth, video.videoHeight))
				return {
					x: 0,
					y: 0,
					width: video.videoWidth,
					height: video.videoHeight,
					downScaledWidth: Math.round(video.videoWidth * scale),
					downScaledHeight: Math.round(video.videoHeight * scale),
				}
			},
		})
		await scanner.start()
		camAvailable.value = true
	} catch {
		camAvailable.value = false
		scanner = null
	}
}

function stopScanner() {
	if (scanner) {
		scanner.destroy()
		scanner = null
	}
}

async function onScan(scanResult) {
	const code = scanResult.data
	if (!code || scanBusy.value || (screen.value !== "home" && screen.value !== "grid")) return
	const now = Date.now()
	if (code === lastScanCode && now - lastScanAt < SCAN_COOLDOWN_MS) return
	lastScanCode = code
	lastScanAt = now

	scanBusy.value = true
	try {
		if (offline.value && canPunchOffline.value) {
			showResult(await enqueueBadge(code))
			return
		}
		try {
			showResult(await punchBadge.submit({ badge_id: code, device_id: DEVICE_ID }))
		} catch (err) {
			if (!(isTransportError(err) && canPunchOffline.value)) throw err
			goOffline()
			showResult(await enqueueBadge(code))
		}
	} catch (err) {
		scanError.value = offlineMessage(err) || noteError(err)
		clearTimeout(scanErrorTimer)
		scanErrorTimer = setTimeout(() => (scanError.value = ""), 3000)
	} finally {
		scanBusy.value = false
	}
}

// Scanner runs on home AND grid (badge always wins); the video element moves
// between the two screens in the DOM, so re-bind the scanner on switch.
watch(screen, async (value) => {
	stopScanner()
	if (value === "home" || value === "grid") await startScanner()
})

// ---- confirmation + undo ----

let undoTimer = null

function showResult(res) {
	result.value = res
	if (soundsEnabled.value) playPunchSound(res.log_type)
	undoDone.value = false
	undoLeft.value = CONFIRM_SECONDS
	screen.value = "done"
	clearInterval(undoTimer)
	undoTimer = setInterval(() => {
		undoLeft.value -= 1
		if (undoLeft.value <= 0) {
			clearInterval(undoTimer)
			reset()
		}
	}, 1000)
}

async function doUndo() {
	clearInterval(undoTimer)
	undoLeft.value = 0
	try {
		if (result.value.offline) {
			setQueue(queue.value.filter((punch) => punch.client_uuid !== result.value.client_uuid))
		} else {
			await undoPunch.submit({ checkin: result.value.name, device_id: DEVICE_ID })
		}
		undoDone.value = true
	} catch (err) {
		scanError.value = noteError(err)
	}
	setTimeout(reset, 1500)
}

function reset() {
	clearInterval(undoTimer)
	screen.value = "home"
	selected.value = null
	pin.value = ""
	error.value = ""
	undoDone.value = false
	undoLeft.value = 0
	if (!offline.value) refresh(employees)
}

// ---- idle fallback: grid/pin return to the clock after inactivity ----

let idleTimer = null

function armIdleTimer() {
	clearTimeout(idleTimer)
	if (screen.value === "grid" || screen.value === "pin") {
		idleTimer = setTimeout(reset, IDLE_BACK_MS)
	}
}

watch(screen, armIdleTimer)

// ---- connection state ----
// The kiosk cannot tell *why* the site stopped answering: a proxy error page, a
// restart during a deployment and a dropped network all look identical from here,
// and every operator signals them differently. So there is exactly one state —
// "we are not being served" — and it clears itself once a request works again.

const RECONNECT_MS = 15_000
const offline = ref(false)
let reconnectTimer = null

// A Frappe error carries `messages` or `exc_type`. Anything else — an HTML error
// page that never parsed as JSON, an aborted request — is a transport problem.
// Without this test the kiosk puts a raw JavaScript message on the wall.
function isTransportError(err) {
	return !(err?.messages?.length || err?.exc_type)
}

function goOffline() {
	if (offline.value) return
	offline.value = true
	reconnectTimer = setInterval(tryReconnect, RECONNECT_MS)
}

// `resource.reload()` records the error AND rethrows it, and no call site awaits
// it — without this wrapper a terminal running for weeks collects unhandled
// rejections, the only forensic trail it has.
function refresh(resource) {
	return resource.reload().catch(goOffline)
}

// Retry with the request the kiosk needs anyway and judge it by whether it
// returned data — no reading of status codes, which every setup uses differently.
async function tryReconnect() {
	await refresh(kioskConfig)
	if (kioskConfig.error) {
		// The server answered, but not with data — after a cold start from the
		// offline cache that is usually an expired session. A real page load lets
		// the token login in /kiosk run again.
		if (!isTransportError(kioskConfig.error)) reloadPage()
		return
	}
	clearInterval(reconnectTimer)
	reconnectTimer = null
	offline.value = false
	error.value = ""
	scanError.value = ""
	refresh(employees)
	sendHeartbeat()
}

// at most once every five minutes, so a server that keeps refusing cannot put the
// wall terminal into a reload loop
function reloadPage() {
	try {
		const last = Number(window.localStorage.getItem("timeclock.reload_at") || 0)
		if (Date.now() - last < 300_000) return
		window.localStorage.setItem("timeclock.reload_at", String(Date.now()))
	} catch {
		return
	}
	window.location.reload()
}

// the auto-fetched resources fail on their own, without passing through noteError
watch([() => employees.error, () => kioskConfig.error], ([empError, configError]) => {
	if (empError || configError) goOffline()
})

// ---- helpers ----

// Errors the kiosk raised itself (could not store a punch, not a badge) carry
// their message ready for the screen; everything else goes through noteError,
// which never puts a raw transport error on the wall.
function kioskError(message) {
	return Object.assign(new Error(message), { isKioskError: true })
}

function offlineMessage(err) {
	return err?.isKioskError ? err.message : ""
}

// Records the connection state as a side effect — hence not just "errorMessage".
function noteError(err) {
	if (isTransportError(err)) {
		goOffline()
		return t("server_unreachable")
	}
	return err.messages?.[0] || err.message || t("error_fallback")
}

// Only colors the frappe-ui preset actually ships (no rose/sky/indigo/fuchsia there)
const AVATAR_COLORS = [
	"bg-red-600",
	"bg-orange-600",
	"bg-amber-600",
	"bg-green-600",
	"bg-teal-600",
	"bg-cyan-600",
	"bg-blue-600",
	"bg-violet-600",
	"bg-purple-600",
	"bg-pink-600",
]

function avatarColor(name) {
	let hash = 0
	for (const ch of name || "") hash = (hash * 31 + ch.codePointAt(0)) % 997
	return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

function initials(name) {
	const parts = (name || "").trim().split(/\s+/)
	return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase()
}

function formatTime(time) {
	return String(time).slice(11, 16)
}

// "seit 08:02", or "seit Di 17:45" when the last IN was not today (forgotten checkout)
function sinceLabel(lastTime) {
	const s = String(lastTime || "")
	const hhmm = s.slice(11, 16)
	const localToday = new Date(Date.now() + clockOffset)
	const y = localToday.getFullYear()
	const m = String(localToday.getMonth() + 1).padStart(2, "0")
	const d = String(localToday.getDate()).padStart(2, "0")
	if (s.slice(0, 10) === `${y}-${m}-${d}`) return hhmm
	const wd = new Date(s.replace(" ", "T")).toLocaleDateString(locale.value, { weekday: "short" })
	return `${wd} ${hhmm}`
}

// Live clock + date (server-synced via clockOffset)
const clock = ref("")
const today = ref("")
let clockTimer
let resyncTimer
let heartbeatTimer
function tick() {
	const now = new Date(Date.now() + clockOffset)
	clock.value = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
	today.value = now.toLocaleDateString(locale.value, {
		weekday: "long",
		day: "numeric",
		month: "long",
		year: "numeric",
	})
}
onMounted(() => {
	refresh(kioskConfig)
	refresh(employees)
	tick()
	clockTimer = setInterval(tick, 5_000)
	// hourly re-sync keeps the offset fresh (drift, DST) and picks up
	// Timeclock Settings changes without a page reload
	resyncTimer = setInterval(() => refresh(kioskConfig), 3_600_000)
	heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_MS)
	setTimeout(sendHeartbeat, 2_000)
	startScanner()
	// browsers unlock audio only after a user gesture; badge-only users may never
	// tap, so grab the very first pointer contact anywhere on the page
	window.addEventListener("pointerdown", unlockSound, { once: true })
	// any touch keeps grid/pin alive; without touches they fall back to the clock
	window.addEventListener("pointerdown", armIdleTimer)
})
onUnmounted(() => {
	clearInterval(clockTimer)
	clearInterval(resyncTimer)
	clearInterval(heartbeatTimer)
	clearInterval(reconnectTimer)
	clearInterval(undoTimer)
	clearTimeout(idleTimer)
	window.removeEventListener("pointerdown", armIdleTimer)
	stopScanner()
})
</script>

<style scoped>
.confirm-pop {
	animation: confirm-pop 0.35s cubic-bezier(0.2, 1.6, 0.4, 1);
}
@keyframes confirm-pop {
	from {
		transform: scale(0.3);
		opacity: 0;
	}
	to {
		transform: scale(1);
		opacity: 1;
	}
}
</style>
