frappe.ui.form.on("Timeclock Queued Punch", {
	refresh(frm) {
		if (frm.doc.status !== "Quarantine" || !frm.perm[0]?.write) return;

		frm.add_custom_button(__("Book Anyway"), () => {
			const fields = [];
			if (!frm.doc.employee) {
				fields.push({ fieldname: "employee", fieldtype: "Link", options: "Employee", label: __("Employee"), reqd: 1 });
			}
			fields.push({
				fieldname: "log_type",
				fieldtype: "Select",
				options: "IN\nOUT",
				label: __("Log Type"),
				default: frm.doc.log_type || "IN",
				reqd: 1,
			});
			frappe.prompt(
				fields,
				(values) =>
					frappe
						.call("timeclock.api.book_queued_punch", { name: frm.doc.name, ...values })
						.then(() => frm.reload_doc()),
				__("Book this punch as an Employee Checkin"),
				__("Book")
			);
		});

		frm.add_custom_button(__("Discard"), () =>
			frappe.confirm(__("Discard this punch? It stays here for the record but is never booked."), () =>
				frappe.call("timeclock.api.discard_queued_punch", { name: frm.doc.name }).then(() => frm.reload_doc())
			)
		);
	},
});
