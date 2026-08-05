app_name = "timeclock"
app_title = "Timeclock"
app_publisher = "Adomio · Yücel & Tirgil GbR"
app_description = (
	"Kiosk time & attendance terminal for Frappe HR (tablet kiosk, employee grid + PIN, QR badge)"
)
app_email = "mitgravur@gmail.com"
app_license = "gpl-3.0"

# Apps
# ------------------

required_apps = ["hrms"]

# Installation
# ------------

after_install = "timeclock.install.after_install"
after_migrate = "timeclock.install.after_migrate"

# App tile in the Desk launcher — admins only (employees never see the app)
add_to_apps_screen = [
	{
		"name": "timeclock",
		"logo": "/assets/timeclock/logo.svg",
		"title": "Timeclock",
		"route": "/app/timeclock",
		"has_permission": "timeclock.permissions.has_app_permission",
	}
]

# HR buttons (Generate/Print Badge) on the Employee form
doctype_js = {"Employee": "public/js/employee.js"}
# Timeclock-filtered employee list links straight to the Time Clock tab
doctype_list_js = {"Employee": "public/js/employee_list.js"}

# QR rendering for the 'Timeclock Badge' print format
jinja = {"methods": ["timeclock.badge.timeclock_badge_qr_svg"]}

# The kiosk writes checkins in realtime; keep Shift Type.last_sync_of_checkin
# current so HRMS auto attendance actually processes them (normally the
# biometric sync tool advances that field).
scheduler_events = {"hourly": ["timeclock.tasks.update_last_sync_of_checkin"]}

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "timeclock",
# 		"logo": "/assets/timeclock/logo.png",
# 		"title": "Timeclock",
# 		"route": "/timeclock",
# 		"has_permission": "timeclock.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/timeclock/css/timeclock.css"
# app_include_js = "/assets/timeclock/js/timeclock.js"

# include js, css files in header of web template
# web_include_css = "/assets/timeclock/css/timeclock.css"
# web_include_js = "/assets/timeclock/js/timeclock.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "timeclock/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "timeclock/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "timeclock.utils.jinja_methods",
# 	"filters": "timeclock.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "timeclock.install.before_install"
# after_install = "timeclock.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "timeclock.uninstall.before_uninstall"
# after_uninstall = "timeclock.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "timeclock.utils.before_app_install"
# after_app_install = "timeclock.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "timeclock.utils.before_app_uninstall"
# after_app_uninstall = "timeclock.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "timeclock.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "timeclock.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"timeclock.tasks.all"
# 	],
# 	"daily": [
# 		"timeclock.tasks.daily"
# 	],
# 	"hourly": [
# 		"timeclock.tasks.hourly"
# 	],
# 	"weekly": [
# 		"timeclock.tasks.weekly"
# 	],
# 	"monthly": [
# 		"timeclock.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "timeclock.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "timeclock.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "timeclock.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "timeclock.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["timeclock.utils.before_request"]
# after_request = ["timeclock.utils.after_request"]

# Job Events
# ----------
# before_job = ["timeclock.utils.before_job"]
# after_job = ["timeclock.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"timeclock.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
