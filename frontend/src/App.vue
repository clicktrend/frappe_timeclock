<template>
	<div class="flex h-screen flex-col bg-[#0f1115] text-zinc-100">
		<!-- Screen: home — clock-first idle like commercial terminals, badge scan active -->
		<main v-if="screen === 'home'" class="flex flex-1 flex-col items-center justify-center gap-2 p-6">
			<div class="font-mono text-[7rem] font-semibold leading-none tracking-tight sm:text-[9rem]">
				{{ clock }}
			</div>
			<div class="text-2xl text-zinc-400">{{ today }}</div>

			<!-- Badge prompt / scanner state -->
			<div class="mt-12 flex flex-col items-center gap-3">
				<template v-if="camAvailable">
					<div class="relative flex h-24 w-24 items-center justify-center">
						<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500/20"></span>
						<span class="relative flex h-20 w-20 items-center justify-center rounded-full bg-zinc-900 text-5xl ring-1 ring-zinc-700">🪪</span>
					</div>
					<div class="text-xl font-medium text-zinc-200">Bitte Badge vorhalten</div>
					<div v-if="scanError" class="text-lg font-medium text-red-400">{{ scanError }}</div>
					<div v-else-if="scanBusy" class="text-base text-zinc-400">Wird gelesen …</div>
					<div v-else class="flex items-center gap-2 text-sm text-zinc-500">
						<span class="relative flex h-2 w-2">
							<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
							<span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
						</span>
						Scanner bereit
					</div>
				</template>
				<template v-else>
					<div class="text-6xl" aria-hidden="true">⚠️</div>
					<div class="text-xl font-semibold text-amber-400">Badge-Scanner nicht bereit</div>
					<div class="text-sm text-zinc-500">Bitte unten per Auswahl + PIN stempeln und den Admin informieren.</div>
				</template>
			</div>

			<button
				class="mt-12 rounded-2xl px-10 py-5 text-xl font-medium shadow-lg transition active:scale-95"
				:class="camAvailable ? 'bg-zinc-900 text-zinc-200 ring-1 ring-zinc-700' : 'bg-blue-600 text-white'"
				@click="screen = 'grid'"
			>
				Ohne Badge stempeln
			</button>

			<!-- hidden (or preview) camera element — must stay rendered for frame grabbing -->
			<video ref="videoEl" :class="videoClass"></video>
		</main>

		<!-- Screen: employee grid (PIN path), scanner stays active -->
		<main v-else-if="screen === 'grid'" class="flex min-h-0 flex-1 flex-col">
			<header class="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
				<button class="flex items-center gap-2 rounded-xl px-4 py-2 text-lg text-zinc-300 transition active:scale-95 active:bg-zinc-800" @click="reset">
					<span class="text-2xl leading-none">‹</span> Zurück
				</button>
				<div class="text-lg font-medium text-zinc-400">Mitarbeiter wählen</div>
				<div class="font-mono text-2xl text-zinc-300">{{ clock }}</div>
			</header>

			<div class="min-h-0 flex-1 overflow-y-auto p-6">
				<div v-if="employees.loading" class="mt-20 text-center text-lg text-zinc-400">Lade Mitarbeiter …</div>
				<div v-else-if="employees.error" class="mt-20 text-center text-lg text-red-400">
					Keine Verbindung oder keine Berechtigung.<br />
					<span class="text-sm text-zinc-500">Kiosk-Benutzer anmelden und Seite neu laden.</span>
				</div>
				<div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
					<button
						v-for="emp in employees.data"
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
						<span v-if="emp.last_log_type === 'IN'" class="text-xs text-emerald-400">seit {{ sinceLabel(emp.last_time) }}</span>
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
					{{ dir === "IN" ? "Kommen" : "Gehen" }}
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

			<button class="mt-2 text-lg text-zinc-500 underline" @click="reset">Abbrechen</button>
		</main>

		<!-- Screen: confirmation (+ undo window) — name, action, big time -->
		<main
			v-else
			class="flex flex-1 flex-col items-center justify-center gap-3"
			:class="result.log_type === 'IN' ? 'bg-emerald-600' : 'bg-orange-500'"
		>
			<!-- explicit rem sizes: the frappe-ui preset shrinks the named text-* scale,
			     but this screen must be readable from across the room -->
			<div class="confirm-pop text-[5.5rem] leading-none text-white">✓</div>
			<div class="text-[1.75rem] font-medium text-white/90">{{ result.employee_name }}</div>
			<div class="text-[3.25rem] font-bold leading-tight text-white">
				{{ result.log_type === "IN" ? "Kommt" : "Geht" }}
			</div>
			<div class="mt-2 font-mono text-[4.5rem] font-semibold leading-none text-white">
				{{ formatTime(result.time) }} Uhr
			</div>
			<div class="mt-2 text-[1.1rem] text-white/80">Zeit wurde erfolgreich gespeichert</div>
			<button
				v-if="undoLeft > 0"
				class="mt-8 rounded-2xl bg-white/20 px-10 py-4 text-[1.4rem] font-medium text-white transition active:scale-95"
				@click="doUndo"
			>
				Rückgängig ({{ undoLeft }})
			</button>
			<div v-if="undoDone" class="text-[1.2rem] text-white/90">Storniert.</div>
		</main>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import QrScanner from "qr-scanner"
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"

import { playPunchSound, unlockSound } from "./sound.js"

const DEVICE_ID = new URLSearchParams(window.location.search).get("device") || "kiosk"
const CONFIRM_SECONDS = 5
const SCAN_COOLDOWN_MS = 4000
const IDLE_BACK_MS = 45_000

const screen = ref("home")
const selected = ref(null)
const direction = ref("IN")
const pin = ref("")
const error = ref("")
const punching = ref(false)
const result = ref(null)
const undoLeft = ref(0)
const undoDone = ref(false)

const employees = createResource({
	url: "timeclock.api.get_kiosk_employees",
	auto: true,
})

const kioskConfig = createResource({
	url: "timeclock.api.get_kiosk_config",
	auto: true,
})
const showPreview = computed(() => Boolean(kioskConfig.data?.show_camera_preview))
const soundsEnabled = computed(() => Boolean(kioskConfig.data?.play_sounds))

// The displayed clock is coupled to the SERVER clock (punch timestamps are
// server-side — the display must never disagree with what gets recorded).
// server_time is site-timezone wall time; parsing it as local makes the kiosk
// show site time even if the tablet's clock or timezone is misconfigured.
let clockOffset = 0
watch(
	() => kioskConfig.data,
	(data) => {
		const raw = String(data?.server_time || "")
		const parsed = Date.parse(raw.split(".")[0].replace(" ", "T"))
		if (!Number.isNaN(parsed)) clockOffset = parsed - Date.now()
		tick()
	}
)

const punch = createResource({ url: "timeclock.api.punch" })
const punchBadge = createResource({ url: "timeclock.api.punch_badge" })
const undoPunch = createResource({ url: "timeclock.api.undo_punch" })

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
		showResult(
			await punch.submit({
				employee: selected.value.name,
				log_type: direction.value,
				pin: pin.value,
				device_id: DEVICE_ID,
			})
		)
	} catch (err) {
		error.value = errorMessage(err)
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
		showResult(await punchBadge.submit({ badge_id: code, device_id: DEVICE_ID }))
	} catch (err) {
		scanError.value = errorMessage(err)
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
		await undoPunch.submit({ checkin: result.value.name, device_id: DEVICE_ID })
		undoDone.value = true
	} catch (err) {
		scanError.value = errorMessage(err)
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
	employees.reload()
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

// ---- helpers ----

function errorMessage(err) {
	return err.messages?.[0] || err.message || "Fehler — bitte erneut versuchen"
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
	const wd = new Date(s.replace(" ", "T")).toLocaleDateString("de-DE", { weekday: "short" })
	return `${wd} ${hhmm}`
}

// Live clock + date (server-synced via clockOffset)
const clock = ref("")
const today = ref("")
let clockTimer
let resyncTimer
function tick() {
	const now = new Date(Date.now() + clockOffset)
	clock.value = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
	today.value = now.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
}
onMounted(() => {
	tick()
	clockTimer = setInterval(tick, 5_000)
	// hourly re-sync keeps the offset fresh (drift, DST) and picks up
	// Timeclock Settings changes without a page reload
	resyncTimer = setInterval(() => kioskConfig.reload(), 3_600_000)
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
