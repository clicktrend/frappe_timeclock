frappe.listview_settings["Timeclock Device"] = {
	add_fields: ["status", "outdated", "pending_punches"],
	get_indicator(doc) {
		if (doc.status === "Offline") return [__("Offline"), "red", "status,=,Offline"];
		if (doc.pending_punches > 0) return [__("Syncing"), "orange", "status,=,Online"];
		if (doc.outdated) return [__("Outdated"), "yellow", "outdated,=,1"];
		return [__("Online"), "green", "status,=,Online"];
	},
};
