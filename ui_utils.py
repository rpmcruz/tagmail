# ui_utils.py

import gtk

ui_singleton = None

def set_ui (ui):
	global ui_singleton
	ui_singleton = ui

def ui_update (step, total):
	global ui_singleton
	ui = ui_singleton
	ui.progressbar.show()
	ui.progressbar.set_fraction (float (step) / total)

	while gtk.events_pending():
		gtk.main_iteration(False)

	if step == total:
		ui.progressbar.hide()

def error_msg (title, details):
	windows = gtk.window_list_toplevels()
	if len (windows) > 0:
		parent = windows[0]
	else:
		parent = None

	dialog = gtk.MessageDialog (parent, 0, gtk.MESSAGE_ERROR,
		gtk.BUTTONS_CLOSE, title)
	dialog.format_secondary_text (details)
	dialog.run()
	dialog.destroy()

