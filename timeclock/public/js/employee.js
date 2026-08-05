function timeclock_print_url(frm) {
	return (
		"/printview?doctype=Employee&name=" +
		encodeURIComponent(frm.doc.name) +
		"&format=" +
		encodeURIComponent("Timeclock Badge") +
		"&no_letterhead=1"
	);
}

function timeclock_render_badge_qr(frm) {
	const field = frm.get_field("timeclock_badge_qr");
	if (!field) return;
	if (!frm.doc.timeclock_badge_id) {
		field.$wrapper.empty();
		return;
	}
	frappe
		.call({ method: "timeclock.api.get_badge_qr", args: { employee: frm.doc.name } })
		.then((r) => {
			if (!r.message) {
				field.$wrapper.empty();
				return;
			}
			field.$wrapper.html(`
				<div style="display:flex;align-items:flex-start;gap:20px;padding:6px 0;">
					<div class="tc-badge-qr" style="width:160px;flex-shrink:0;">${r.message}</div>
					<div style="display:flex;flex-direction:column;gap:8px;">
						<a href="${timeclock_print_url(frm)}" target="_blank" class="btn btn-sm btn-default" style="width:fit-content;">
							${__("Print Badge")}
						</a>
						<div class="text-muted" style="font-size:12px;max-width:260px;">
							${__("This QR code is the employee's badge. Print it on the ID card or let them scan it from here.")}
						</div>
					</div>
				</div>
				<style>.tc-badge-qr svg { width: 160px; height: 160px; }</style>
			`);
		});
}

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.timeclock_enabled) return;

		timeclock_render_badge_qr(frm);

		frm.add_custom_button(
			__("Generate Badge"),
			() => {
				const proceed = () =>
					frappe
						.call({ method: "timeclock.api.generate_badge", args: { employee: frm.doc.name } })
						.then(() => {
							frappe.show_alert({ message: __("New badge issued"), indicator: "green" });
							frm.reload_doc();
						});

				if (frm.doc.timeclock_badge_id) {
					frappe.confirm(
						__("Issue a new badge? The current badge stops working immediately."),
						proceed
					);
				} else {
					proceed();
				}
			},
			__("Time Clock")
		);

		if (frm.doc.timeclock_badge_id) {
			frm.add_custom_button(
				__("Print Badge"),
				() => window.open(timeclock_print_url(frm), "_blank"),
				__("Time Clock")
			);
		}
	},
});
