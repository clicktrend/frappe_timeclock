<template>
	<div class="flex h-screen flex-col bg-gray-100">
		<!-- Header -->
		<header class="flex items-center justify-between bg-white px-6 py-3 shadow-sm">
			<h1 class="text-xl font-semibold text-gray-800">Stempeluhr</h1>
			<div class="text-2xl font-mono text-gray-700">{{ clock }}</div>
		</header>

		<!-- Screen: employee grid -->
		<main v-if="screen === 'grid'" class="flex-1 overflow-y-auto p-6">
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

		<!-- Screen: confirmation -->
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
		</main>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { onMounted, onUnmounted, ref } from "vue"

const DEVICE_ID = new URLSearchParams(window.location.search).get("device") || "kiosk"
const CONFIRM_SECONDS = 5

const screen = ref("grid")
const selected = ref(null)
const direction = ref("IN")
const pin = ref("")
const error = ref("")
const punching = ref(false)
const result = ref(null)

const employees = createResource({
	url: "timeclock.api.get_kiosk_employees",
	auto: true,
})

const punch = createResource({ url: "timeclock.api.punch" })

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
		result.value = await punch.submit({
			employee: selected.value.name,
			log_type: direction.value,
			pin: pin.value,
			device_id: DEVICE_ID,
		})
		screen.value = "done"
		setTimeout(reset, CONFIRM_SECONDS * 1000)
	} catch (err) {
		error.value = err.messages?.[0] || err.message || "Fehler — bitte erneut versuchen"
		pin.value = ""
	} finally {
		punching.value = false
	}
}

function reset() {
	screen.value = "grid"
	selected.value = null
	pin.value = ""
	error.value = ""
	employees.reload()
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
})
onUnmounted(() => clearInterval(clockTimer))
</script>
