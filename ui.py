# ui.py

import os, sys, gtk, gconf

from db import *
from account import *
from ui_utils import *

def load_ui (filename):
	builder = gtk.Builder()
	if builder.add_from_file (filename) == 0:
		error_msg ("Data loading error", "Could not load UI file: " + filename)
		sys.exit (-1)
	return builder

def shrink_button (button):
	gtk.rc_parse_string (
		"style \"zero-thickness\"\n" +
		"{\n" +
		"	xthickness = 0\n" +
		"	ythickness = 0\n" +
		"}\n" +
		"widget \"*.smallbutton\" style \"zero-thickness\"")
	button.set_name ("smallbutton")

def set_monospace_font (widget):
	font_desc = widget.get_pango_context().get_font_description()
	font_desc.set_family ("monospace")
	widget.modify_font (font_desc)

class AddAccountUI:
	def __init__ (self, window):
		self.builder = load_ui ("add_account.ui")
		self.param_box = self.builder.get_object ("param_box")
		self.dialog = self.builder.get_object ("dialog")
		self.dialog.set_transient_for (window)
		self.builder.connect_signals (self)

	def run (self):
		if self.dialog.run() == 1:
			type = "test"
			protocol = ""
			if self.get_active ("pop3"):
				type = "pop3"
				if self.get_active ("ssl"):
					protocol = "ssl"
			server = self.get_text ("server")
			username = self.get_text ("username")
			password = self.get_text ("password")
			add_account (type, server, username, password, protocol)
		self.dialog.destroy()

	def get_text (self, attrb):
		return self.builder.get_object (attrb).get_text()

	def get_active (self, attrb):
		return self.builder.get_object(attrb).get_active() == True

	def on_pop3_toggled (self, item):
		self.param_box.set_sensitive (item.get_active())

class EditAccountsUI:
	def __init__ (self, window):
		builder = load_ui ("edit_accounts.ui")
		self.dialog = builder.get_object ("dialog")
		self.dialog.set_transient_for (window)

		button = builder.get_object ("remove_button")
		self.view = builder.get_object ("view")
		button.set_sensitive (False)
		selection = self.view.get_selection()
		selection.connect ("changed", self.on_view_selection_changed, button)
		self.refresh()

		builder.connect_signals (self)

	def run (self):
		self.dialog.run()
		self.dialog.destroy()

	def refresh (self):
		store = gtk.ListStore (str, str, int)
		accounts = list_accounts()
		for a in accounts:
			it = store.append()
			store.set (it, 0, a[2], 1, a[1], 2, a[0])
		self.view.set_model (store)

	def on_add_button_clicked (self, button):
		window = self.dialog.get_transient_for()
		self.dialog.set_sensitive (False)
		AddAccountUI (self.dialog).run()
		self.dialog.set_sensitive (True)
		self.refresh()

	def on_remove_button_clicked (self, button):
		model, it = self.view.get_selection().get_selected()
		if it != None:
			id = model.get(it,2)[0]
			remove_account (id)
			self.refresh()

	def on_view_selection_changed (self, selection, button):
		button.set_sensitive (selection.count_selected_rows() > 0)

class AttrbWidget (gtk.EventBox):
	def __init__(self, ui, label, table, msg_attrb, id):
		gtk.EventBox.__init__(self)
		self.ui = ui
		self.table = table
		self.attrb = msg_attrb
		self.id = id
		builder = load_ui ("attrb.ui")
		builder.get_object("label").set_text (label)
		self.view = builder.get_object("view")
		self.popup = builder.get_object("popup")
		self.favorite_check = builder.get_object ("favorite_check")
		self.widget = builder.get_object("top")
		self.widget.reparent (self)

		conf = gconf.client_get_default()
		self.N = conf.get_int ("/apps/tagmail/N" + str (id))
		if self.N == 0: self.N = 25

		shrink_button (builder.get_object("zoom_in"))
		shrink_button (builder.get_object("zoom_out"))

		self.value_filter = None
		builder.connect_signals (self)
		selection = self.view.get_selection()
		selection.set_mode (gtk.SELECTION_BROWSE)
		selection.connect ("changed", self.on_view_selection_changed)
		self.show()

	def get_value (self):
		model, it = self.view.get_selection().get_selected()
		if it == None or model.get_path(it)[0] == 0:
			return ""
		return model.get (it, 0)[0]

	def unselect (self):
		model = self.view.get_model()
		selection = self.view.get_selection()
		selection.handler_block_by_func(self.on_view_selection_changed)
		selection.select_iter (model.get_iter_first())
		selection.handler_unblock_by_func(self.on_view_selection_changed)

	def do_query(self):
		selected = self.get_value()
		# value, name, count, weight, bg_color, editable
		store = gtk.ListStore (str, str, int, int, str, bool)
		values = list_attrb (self.table)

		values_count = []  # row, name, total, new, is-fav
		for i in values:
			if i[0] == "": continue
			total, new = count_attrb (self.attrb, i[0])
			fav = is_favorite_attrb (self.table, i[0])
			name = i[1]
			if name == "": name = i[0]
			values_count.append ((i, name, total, new, fav))
		def values_count_sort (x, y):
			# fav
			if x[4] and not y[4]: return -1
			if not x[4] and y[4]: return 1
			# new count
			if x[3] > 0 and y[3] == 0: return -1
			if x[3] == 0 and y[3] > 0: return 1
			# total count
			return y[2] - x[2]
		values_count.sort (values_count_sort)

		it = store.append()
		total_count, new_count = count_messages()
		weight = 400
		if new_count > 0:
			weight = 800
		store.set (it, 0, None, 1, "All", 2, total_count, 3, weight, 4, None, 5, False)
		select_it = it

		n = 0
		for i in values_count:
			if n > self.N and i[3] == 0 and not i[4]:
				break
			n += 1

			value = i[0][0]
			name = i[1]
			count = i[2]
			weight = 400
			if i[3] > 0: weight = 800
			bg_color = None
			if i[4]: bg_color = "#ffd2d2"
			it = store.append()			
			store.set (it, 0, value, 1, name, 2, count, 3, weight, 4, bg_color, 5, True)
			if selected == value:
				select_it = it

		selection = self.view.get_selection()
		selection.handler_block_by_func(self.on_view_selection_changed)
		self.view.set_model (store)
		selection.select_iter (select_it)
		selection.handler_unblock_by_func(self.on_view_selection_changed)

	def on_zoom_out_clicked (self, button):
		self.N -= 5
		self.N = max (self.N, 0)
		self.do_query()
		conf = gconf.client_get_default()
		conf.set_int ("/apps/tagmail/N" + str (self.id), self.N)

	def on_zoom_in_clicked (self, button):
		self.N += 5
		self.do_query()
		conf = gconf.client_get_default()
		conf.set_int ("/apps/tagmail/N" + str (self.id), self.N)

	def on_view_selection_changed (self, selection):
		self.ui.do_msg_query_by_attrb (self)

	def on_view_button_press_event (self, view, event):
		if event.button == 3:
			pos = view.get_path_at_pos (int (event.x), int (event.y))
			if pos != None:  # some path selected
				# hack to make it select the item
				event.button = 1
				view.event (event)

				all_item = pos[0][0] == 0
				for i in self.popup.get_children():
					i.set_sensitive (not all_item)  # not All
				if not all_item:
					model = view.get_model()
					it = model.get_iter (pos[0])
					value = model.get (it, 0)[0]
					fav = is_favorite_attrb (self.table, value)
					self.favorite_check.handler_block_by_func(self.on_favorite_check_toggled)
					self.favorite_check.set_active (fav)
					self.favorite_check.handler_unblock_by_func(self.on_favorite_check_toggled)
				self.popup.popup (None, None, None, 3, event.time)
			return True
		return False

	def on_name_renderer_edited (self, renderer, path_str, text):
		model = self.view.get_model()
		it = model.get_iter_from_string (path_str)
		value = model.get (it, 0)[0]
		name_attrb (self.table, value, text)
		self.do_query()

	def on_rename_item_activate (self, item):
		model, it = self.view.get_selection().get_selected()
		if it != None:
			path = model.get_path (it)
			column = self.view.get_column (0)
			self.view.set_cursor (path, column, True)
	
	def on_favorite_check_toggled (self, check):
		model, it = self.view.get_selection().get_selected()
		if it != None:
			value = model.get (it, 0)[0]
			favorite_attrb (self.table, value, check.get_active())
			self.do_query()

SENDMAIL = "/usr/sbin/sendmail" # sendmail location

class SendmailSetupUI:
	def __init__ (self, window):
		builder = load_ui ("setup_sendmail.ui")
		self.email_entry = builder.get_object ("email_entry")

		operational = os.path.exists (SENDMAIL)
		if operational:
			stock = gtk.STOCK_YES
			label = "Sendmail installed"
		else:
			stock = gtk.STOCK_NO
			label = "Sendmail is NOT installed"
		status_img = builder.get_object ("status_img")
		status_label = builder.get_object ("status_label")
		status_img.set_from_stock(stock, gtk.ICON_SIZE_BUTTON)
		status_label.set_text (label)
		ok_button = builder.get_object ("ok_button")
		ok_button.set_sensitive (operational)

		self.dialog = builder.get_object ("dialog")
		self.dialog.set_transient_for (window)
		builder.connect_signals (self)

	def run(self):
		ret = ""
		if self.dialog.run() == 1:
			ret = self.email_entry.get_text()
			print "OK:", ret
		self.dialog.destroy()
		return ret

import datetime

def send_mail (parent, _to, cc, subject, body):
	conf = gconf.client_get_default()
	_from = conf.get_string ("/apps/tagmail/from")
	if _from == "" or _from == None:
		_from = SendmailSetupUI (parent).run()
	print "from:", _from
	if _from != "":
		p = os.popen("%s -t" % SENDMAIL, "w")
		p.write("To: %s\n" % _to)
		p.write("Cc: %s\n" % cc)
		p.write("Subject: %s\n" % subject)
		p.write("Date: %s\n" % str(datetime.datetime.now()))
		p.write("User-Agent: Tag Mail\n")
		p.write("\n") # blank line separating headers from body
		p.write(body)
		return p.close()  # error if != 0
	return 0

class ComposerUI:
	def __init__ (self, window):
		builder = load_ui ("composer.ui")
		self.to_entry = builder.get_object ("to_entry")
		self.cc_entry = builder.get_object ("cc_entry")
		self.subject_entry = builder.get_object ("subject_entry")
		self.msg_buffer = builder.get_object ("msg_buffer")

		dialog = builder.get_object ("dialog")
		dialog.set_transient_for (window)
		builder.connect_signals (self)

	def set_fields (self, _to, cc):
		self.to_entry.set_text (_to)
		self.cc_entry.set_text (cc)

	def on_dialog_response (self, dialog, response):
		done = True
		if response == 1:
			_to = self.to_entry.get_text()
			cc = self.cc_entry.get_text()
			subject = self.subject_entry.get_text()
			start, end = self.msg_buffer.get_bounds()
			body = self.msg_buffer.get_text (start, end)
			ret = send_mail (dialog, _to, cc, subject, body)
			if ret != 0:
				dialog = gtk.MessageDialog (dialog, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Sendmail error")
				dialog.format_secondary_text ("Return value: %d" % ret)
				dialog.run()
				dialog.destroy()
				done = False
		if done:
			dialog.destroy()

class MainUI:
	def __init__ (self):
		set_ui (self)
		builder = load_ui ("main.ui")
		self.msg_view = builder.get_object ("msg_view")
		self.msg_paned = builder.get_object ("msg_paned")
		self.body_buffer = builder.get_object ("body_buffer")
		self.header_tag = builder.get_object ("header_tag")
		tag_table = builder.get_object ("tag_table")
		tag_table.add (self.header_tag)
		set_monospace_font (builder.get_object ("body_view"))

		self.side_box = builder.get_object ("side_box")
		self.side_box.pack_start (AttrbWidget(self, "Emails:", "EMAILS", "_FROM", 0), True)
		self.side_box.pack_start (AttrbWidget(self, "Mailing lists:", "MAILING_LISTS", "MAILING_LIST", 1), True)

		self.msg_view.get_selection().connect ("changed", self.on_msg_view_selection_changed)

		self.menubar = builder.get_object ("menubar")
		self.statusbar = builder.get_object ("statusbar")
		self.connect_menu_status_bar (self.menubar, self.statusbar)
		self.progressbar = gtk.ProgressBar()
		self.progressbar.set_size_request (120, 1)
		self.statusbar.pack_start (self.progressbar, False)

		self.author_filter = None
		self.window = builder.get_object ("window")
		self.do_general_query()
		self.set_panoramic_view (False)
		builder.connect_signals (self)

		conf = gconf.client_get_default()
		if not conf.dir_exists ("/apps/tagmail"):
			conf.add_dir ("/apps/tagmail", gconf.CLIENT_PRELOAD_NONE)
			conf.set_bool ("/apps/tagmail/show-statusbar", True)
			conf.set_bool ("/apps/tagmail/panoramic-view", False)
			conf.set_bool ("/apps/tagmail/window-maximize", False)

		conf = gconf.client_get_default()
		check = builder.get_object ("statusbar_check")
		check.set_active (conf.get_bool ("/apps/tagmail/show-statusbar"))
		check = builder.get_object ("panoramic_check")
		check.set_active (conf.get_bool ("/apps/tagmail/panoramic-view"))
		if (conf.get_bool ("/apps/tagmail/window-maximize")):
			self.window.maximize()

	def run (self):
		gtk.main()

	def set_panoramic_view (self, panoramic):
		if panoramic:
			self.msg_paned.set_orientation (gtk.ORIENTATION_HORIZONTAL)
			self.msg_paned.set_position (-1)
			self.window.resize (800, 800)
		else:
			self.msg_paned.set_orientation (gtk.ORIENTATION_VERTICAL)
			self.msg_paned.set_position (100)
			self.window.resize (600, 800)

	def connect_menu_status_bar (self, menubar, statusbar):
		# acts like UIManager::proxy if we used that structure
		for i in menubar.get_children():
			for j in i.get_submenu().get_children():
				j.connect ("select", self.on_menuitem_select, statusbar)
				j.connect ("deselect", self.on_menuitem_deselect, statusbar)

	def on_menuitem_select (self, item, statusbar):
		action = item.get_related_action()
		if action != None:
			statusbar.push (0, action.get_tooltip())

	def on_menuitem_deselect (self, item, statusbar):
		statusbar.pop (0)

	def do_general_query (self):
		self.do_attrb_query()
		self.do_msg_query()

	def do_msg_query_by_attrb (self, attrb):
		for i in self.side_box.get_children():
			if i != attrb:
				i.unselect()
		self.do_msg_query()

	def do_msg_query (self):
		# author, subject, date, content, weight, index
		store = gtk.ListStore (str, str, str, str, int, int)
		attrbs = self.side_box.get_children()
		email = attrbs[0].get_value()
		mailing_list = attrbs[1].get_value()
		msgs = list_messages ("", email, mailing_list)
		for m in msgs:
			if m[8]: weight = 400
			else:
				weight = 800
			it = store.append()
			store.set (it, 0, m[1], 1, m[5], 2, m[7], 3, m[6], 4, weight, 5, m[0])
		self.msg_view.set_model (store)

	def do_attrb_query (self):
		for i in self.side_box.get_children():
			i.do_query()

	# tree-view events

	def on_msg_view_selection_changed (self, selection):
		model, it = selection.get_selected()
		self.body_buffer.set_text ("")
		if it != None:
			content = model.get (it, 3)[0]
			weight = model.get (it, 4)[0]
			id = model.get (it, 5)[0]
			if weight == 800:
				mark_message_as_read (id)
				model.set (it, 4, 400)
				self.do_attrb_query()

			msg = select_message (id)
			header = "Subject: " + msg[5] + "\n"
			header += "From: " + msg[1] + "\n"
			header += "To: " + msg[2] + "\n"
			header += "CC: " + msg[3]
			it = self.body_buffer.get_start_iter()
			self.body_buffer.insert_with_tags (it, header, self.header_tag)
			it = self.body_buffer.get_end_iter()
			self.body_buffer.insert (it, "\n" + content)

	# search entry events

	def on_search_entry_changed (self, entry):
		has_text = len (entry.get_text()) > 0
		entry.set_property ("secondary-icon-sensitive", has_text)
		bg_color = None
		if has_text: bg_color = gtk.gdk.Color (0xf7f7, 0xf7f7, 0xbebe)
		entry.modify_base (gtk.STATE_NORMAL, bg_color)

	def on_search_entry_icon_press (self, entry, icon, event):
		if icon == gtk.ENTRY_ICON_PRIMARY:
			entry.grab_focus()
		else:
			entry.set_text ("")

	# window events

	def on_window_destroy (self, window):
		gtk.main_quit()

	# menu & toolbar actions

	def on_new_account_action_activate (self, action):
		AddAccountUI(self.window).run()

	def on_get_mail_action_activate (self, action):
		for i in self.menubar.get_children()[0].get_submenu().get_children():
			action = i.get_related_action()
			if action != None:
				action.set_sensitive(False)

		try:
			refresh_accounts()
		except TagException as ex:
			error_msg (ex.title + " error", ex.details)
		self.do_general_query()

		for i in self.menubar.get_children()[0].get_submenu().get_children():
			action = i.get_related_action()
			if action != None:
				action.set_sensitive(True)

	def on_quit_action_activate (self, action):
		gtk.main_quit()

	def on_edit_accounts_action_activate (self, action):
		EditAccountsUI (self.window).run()

	def on_save_as_action_activate (self, action):
		dialog = gtk.FileChooserDialog ("", self.window, gtk.FILE_CHOOSER_ACTION_SAVE,
			(gtk.STOCK_CANCEL, 0, gtk.STOCK_SAVE, 1))
		dialog.set_local_only (True)
		if dialog.run() == 1:
			filename = dialog.get_filename()
			import shutil
			ori = os.path.join (os.path.expanduser('~'), ".tagmail")
			shutil.copy (ori, filename)
		dialog.destroy()

	def on_mail_action_activate (self, action):
		ComposerUI (self.window)

	def on_reply_action_activate (self, action):
		model, it = self.msg_view.get_selection().get_selected()
		if it != None:
			id = model.get (it, 5)[0]
			msg = select_message (id)
			ui = ComposerUI (self.window)
			ui.set_fields (msg[1], msg[3])

	def on_all_read_action_activate (self, action):
		mark_all_message_as_read()
		self.do_general_query()

	def on_statusbar_toggled (self, item):
		active = item.get_active()
		if active:
			self.statusbar.show()
		else:
			self.statusbar.hide()
		conf = gconf.client_get_default()
		conf.set_bool ("/apps/tagmail/show-statusbar", active)

	def on_panoramic_toggled (self, item):
		active = item.get_active()
		self.set_panoramic_view (active)
		conf = gconf.client_get_default()
		conf.set_bool ("/apps/tagmail/panoramic-view", active)

	def on_window_window_state_event (self, window, event):
		maximized = event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED
		conf = gconf.client_get_default()
		conf.set_bool ("/apps/tagmail/window-maximize", maximized)

