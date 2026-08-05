// Confirmation sounds via Web Audio (no audio assets needed): rising two-tone
// for IN, falling two-tone for OUT. Browsers keep the AudioContext suspended
// until a user gesture — unlockSound() is wired to the first pointerdown, and
// kiosk WebViews (FreeKiosk) can allow media without a gesture anyway.

let ctx = null

function ensureContext() {
	if (!ctx) {
		const AudioCtx = window.AudioContext || window.webkitAudioContext
		if (!AudioCtx) return null
		ctx = new AudioCtx()
	}
	if (ctx.state === "suspended") ctx.resume()
	return ctx
}

export function unlockSound() {
	ensureContext()
}

function beep(audio, frequency, startAt, duration = 0.12, volume = 0.25) {
	const osc = audio.createOscillator()
	const gain = audio.createGain()
	osc.type = "sine"
	osc.frequency.value = frequency
	gain.gain.setValueAtTime(0, startAt)
	gain.gain.linearRampToValueAtTime(volume, startAt + 0.01)
	gain.gain.exponentialRampToValueAtTime(0.001, startAt + duration)
	osc.connect(gain)
	gain.connect(audio.destination)
	osc.start(startAt)
	osc.stop(startAt + duration + 0.02)
}

export function playPunchSound(logType) {
	const audio = ensureContext()
	if (!audio) return
	const now = audio.currentTime
	if (logType === "IN") {
		beep(audio, 880, now)
		beep(audio, 1175, now + 0.14)
	} else {
		beep(audio, 784, now)
		beep(audio, 587, now + 0.14)
	}
}
