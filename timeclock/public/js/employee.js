frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.timeclock_enabled) return;

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
				() => {
					const url =
						`/printview?doctype=Employee&name=${encodeURIComponent(frm.doc.name)}` +
						`&format=${encodeURIComponent("Timeclock Badge")}&no_letterhead=1`;
					window.open(url, "_blank");
				},
				__("Time Clock")
			);
		}
	},
});
