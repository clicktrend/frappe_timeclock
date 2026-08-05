// Loaded after hrms/erpnext list settings (timeclock is installed last), so we
// extend instead of overwrite. While the timeclock filter is active (= the list
// was opened from the Timeclock workspace shortcut), employee rows link straight
// to the Time Clock tab via URL anchor — frappe opens the tab whose Tab Break
// fieldname matches the hash.
frappe.listview_settings["Employee"] = frappe.listview_settings["Employee"] || {};

frappe.listview_settings["Employee"].get_form_link = (doc) => {
	// list rows don't carry a doctype field — this is always the Employee list.
	// Keep the user in whichever desk UI they are in (v16 /desk vs classic /app).
	const prefix = window.location.pathname.startsWith("/desk") ? "/desk" : "/app";
	let link = prefix + "/employee/" + encodeURIComponent(doc.name);
	try {
		const filters = cur_list?.filter_area?.get() || [];
		if (filters.some((f) => f[1] === "timeclock_enabled")) {
			link += "#timeclock_tab";
		}
	} catch (e) {
		// no list context — keep the plain link
	}
	return link;
};
