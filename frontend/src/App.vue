<template>
	<div class="flex h-screen flex-col bg-gray-100">
		<!-- Header -->
		<header class="flex items-center justify-between bg-white px-6 py-3 shadow-sm">
			<h1 class="text-xl font-semibold text-gray-800">Stempeluhr</h1>
			<div class="text-2xl font-mono text-gray-700">{{ clock }}</div>
		</header>

		<!-- Screen: employee grid + badge camera -->
		<main v-if="screen === 'grid'" class="flex flex-1 overflow-hidden">
			<div class="flex-1 overflow-y-auto p-6">
				<div v-if="employees.loading" class="mt-20 text-center text-lg text-gray-500">Lade Mitarbeiter …</div>
				<div v-else-if="employees.error" class="mt-20 text-center text-lg text-red-600">
					Keine Verbindung oder keine Berechtigung.<br />
					<span class="text-sm text-gray-500">Kiosk-Benutzer anmelden und Seite neu laden.</span>
				</div>
				<div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
					<button
						v-for="emp in employees.data"
						:key="emp.name"
						class="flex h-28 flex-col items-center justify-center rounded-xl bg-white text-lg font-medium text-gray-800 shadow transition active:scale-95 active:bg-blue-50"
						@click="selectEmployee(emp)"
					>
						<span>{{ emp.employee_name }}</span>
						<span v-if="emp.last_time" class="mt-1 text-xs font-normal text-gray-400">
							zuletzt {{ emp.last_log_type === "IN" ? "gekommen" : "gegangen" }}
						</span>
					</button>
				</div>
			</div>

			<!-- Badge scanner panel. Privacy default: the camera scans WITHOUT showing its
			     image (nobody should feel filmed) — the video element stays rendered at
			     1x1px/opacity-0 so frame grabbing keeps working. Admins can opt into a live
			     preview via Timeclock Settings ("Show Camera Preview on Kiosk"). If the
			     camera could not be started, the panel says so loudly instead. -->
			<aside
				class="relative flex w-80 flex-col items-center justify-center gap-4 border-l border-gray-200 bg-white p-6 text-center"
			>
				<video
					ref="videoEl"
					:class="
						showPreview && camAvailable
							? 'aspect-square w-full rounded-xl bg-black object-cover'
							: 'pointer-events-none absolute h-px w-px opacity-0'
					"
				></video>

				<template v-if="camAvailable">
					<div v-if="!showPreview" class="text-8xl" aria-hidden="true">🪪</div>
					<div class="text-xl font-semibold text-gray-800">Badge vorhalten</div>
					<div v-if="scanError" class="text-lg font-medium text-red-600">{{ scanError }}</div>
					<div v-else-if="scanBusy" class="text-base text-gray-600">Wird gelesen …</div>
					<div v-else class="flex items-center gap-2 text-sm text-gray-400">
						<span class="relative flex h-2.5 w-2.5">
							<span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
							<span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500"></span>
						</span>
						Scanner bereit — Ausweis-QR kurz vorhalten
					</div>
				</template>

				<template v-else>
					<div class="text-7xl" aria-hidden="true">⚠️</div>
					<div class="text-xl font-semibold text-amber-700">Terminal nicht bereit</div>
					<div class="text-sm text-gray-500">
						Kamera konnte nicht gestartet werden — Badge-Scan ist deaktiviert.<br />
						Bitte per Auswahl + PIN stempeln und den Admin informieren.
					</div>
				</template>
			</aside>
		</main>

		<!-- Screen: direction + PIN -->
		<main v-else-if="screen === 'pin'" class="flex flex-1 flex-col items-center justify-center gap-6 p-6">
			<div class="text-2xl font-semibold text-gray-800">{{ selected.employee_name }}</div>

			<div class="flex gap-4">
				<button
					v-for="dir in ['IN', 'OUT']"
					:key="dir"
					class="rounded-xl px-10 py-5 text-xl font-semibold shadow transition active:scale-95"
					:class="
						direction === dir
							? dir === 'IN'
								? 'bg-green-600 text-white'
								: 'bg-orange-500 text-white'
							: 'bg-white text-gray-700'
					"
					@click="direction = dir"
				>
					{{ dir === "IN" ? "Kommen" : "Gehen" }}
				</button>
			</div>

			<!-- PIN display -->
			<div class="flex h-10 items-center gap-3">
				<span
					v-for="i in 6"
					:key="i"
					class="h-4 w-4 rounded-full border-2 border-gray-400"
					:class="{ 'bg-gray-700 border-gray-700': pin.length >= i }"
				/>
			</div>
			<div v-if="error" class="text-lg font-medium text-red-600">{{ error }}</div>

			<!-- PIN pad -->
			<div class="grid grid-cols-3 gap-3">
				<button
					v-for="key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', 'OK']"
					:key="key"
					class="h-20 w-24 rounded-xl text-2xl font-semibold shadow transition active:scale-95"
					:class="
						key === 'OK'
							? 'bg-blue-600 text-white disabled:opacity-40'
							: key === 'C'
								? 'bg-gray-200 text-gray-700'
								: 'bg-white text-gray-800'
					"
					:disabled="key === 'OK' && (pin.length < 4 || punching)"
					@click="pressKey(key)"
				>
					{{ key }}
				</button>
			</div>

			<button class="mt-2 text-lg text-gray-500 underline" @click="reset">Abbrechen</button>
		</main>

		<!-- Screen: confirmation (+ undo window) -->
		<main
			v-else
			class="flex flex-1 flex-col items-center justify-center gap-4"
			:class="result.log_type === 'IN' ? 'bg-green-600' : 'bg-orange-500'"
		>
			<div class="text-6xl text-white">✓</div>
			<div class="text-3xl font-semibold text-white">
				{{ result.log_type === "IN" ? "Willkommen" : "Bis bald" }}, {{ firstName(result.employee_name) }}!
			</div>
			<div class="text-xl text-white/90">
				{{ result.log_type === "IN" ? "Eingestempelt" : "Ausgestempelt" }} um {{ formatTime(result.time) }}
			</div>
			<button
				v-if="undoLeft > 0"
				class="mt-6 rounded-xl bg-white/20 px-8 py-4 text-xl font-medium text-white shadow transition active:scale-95"
				@click="doUndo"
			>
				Rückgängig ({{ undoLeft }})
			</button>
			<div v-if="undoDone" class="text-lg text-white/90">Storniert.</div>
		</main>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import QrScanner from "qr-scanner"
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"

const DEVICE_ID = new URLSearchParams(window.location.search).get("device") || "kiosk"
const CONFIRM_SECONDS = 5
const SCAN_COOLDOWN_MS = 4000

const screen = ref("grid")
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

const videoEl = ref(null)
const camAvailable = ref(true)
const scanBusy = ref(false)
const scanError = ref("")
let scanner = null
let lastScanCode = ""
let lastScanAt = 0
let scanErrorTimer = null

async function startScanner() {
	await nextTick()
	if (!videoEl.value || scanner) return
	try {
		scanner = new QrScanner(videoEl.value, onScan, {
			returnDetailedScanResult: true,
			maxScansPerSecond: 4,
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
	if (!code || scanBusy.value || screen.value !== "grid") return
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

watch(screen, (value) => {
	if (value === "grid") startScanner()
	else stopScanner()
})

// ---- confirmation + undo ----

let undoTimer = null

function showResult(res) {
	result.value = res
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
	screen.value = "grid"
	selected.value = null
	pin.value = ""
	error.value = ""
	undoDone.value = false
	undoLeft.value = 0
	employees.reload()
}

// ---- helpers ----

function errorMessage(err) {
	return err.messages?.[0] || err.message || "Fehler — bitte erneut versuchen"
}

function firstName(fullName) {
	return (fullName || "").split(" ")[0]
}

function formatTime(time) {
	return String(time).slice(11, 16)
}

// Live clock in the header
const clock = ref("")
let clockTimer
function tick() {
	clock.value = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
}
onMounted(() => {
	tick()
	clockTimer = setInterval(tick, 10_000)
	startScanner()
})
onUnmounted(() => {
	clearInterval(clockTimer)
	clearInterval(undoTimer)
	stopScanner()
})
</script>
