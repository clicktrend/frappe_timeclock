frappe.listview_settings["Timeclock Queued Punch"] = {
	add_fields: ["status", "attendance"],
	get_indicator(doc) {
		if (doc.status === "Quarantine") return [__("Quarantine"), "orange", "status,=,Quarantine"];
		if (doc.status === "Discarded") return [__("Discarded"), "gray", "status,=,Discarded"];
		if (doc.attendance) return [__("Check Attendance"), "yellow", "status,=,Booked"];
		return [__("Booked"), "green", "status,=,Booked"];
	},
};
