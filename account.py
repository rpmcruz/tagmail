# account.py

from db import *
from utils import *
from ui_utils import *

# Pop3

import poplib, socket

def refresh_pop3 (account):
	try:
		server = account[2]
		use_ssl = account[5] == "ssl"
		# FIXME: set a timeout
		if use_ssl:
			pop = poplib.POP3_SSL (server)
		else:
			pop = poplib.POP3 (server)
		pop.user (account[3])
		pop.pass_ (account[4])

		last_msg = account[6]
		num = len (pop.list()[1])  # FIXME: check less expensive way to get msgs-nb
		for n in range (last_msg, num):
			msg = pop.retr(n+1)[1]

			reading_headers = True
			_from = _to = cc = subject = date = mailing_list = ""
			body = ""
			for l in msg:
				#l = l.encode("utf-8")
				if reading_headers:
					i = l.find (":")
					if i != -1:
						header = l[:i]
						content = l[i+2:]
						if header == "From":
							_from = content
						elif header == "To":
							_to = content
						elif header == "Cc":
							cc = content
						elif header == "Subject":
							subject = content
						elif header == "Date":
							date = content
						elif header == "List-ID":
							mailing_list = content
						#headers [header] = content
					if l == "":
						reading_headers = False
				else:
					body += l + "\n"

			#body = body.encode ("utf-8")
			if not subject.startswith ("[SPAM]"):
				add_message (_from, _to, cc, mailing_list, subject, body, date)
				ui_update (n, num-last_msg)
		pop.quit()
		set_account_last_message (account[0], num)
	except poplib.error_proto, msg:
		raise TagException ("POP3 protocol", msg)
	except socket.error, msg:
		raise TagException ("Connection", msg)
	return True

# Dummy

msgs = [
	("artur@email.pt", "Aaaaaaaaaa", "05-06-2010", "Hoje constipei-me"),
	("beatriz@email.pt", "Bbbbbb", "05-06-2010", "Hoje molhei-me"),

	("artur@email.pt", "Ccccccc", "05-06-2010", "Hoje queimei-me"),
	("fatima@email.pt", "Dddddddd", "05-06-2010", "Hoje fascinei-me"),

	("beatriz@email.pt", "Eeeeeeee", "05-06-2010", "Hoje consciencializei-me"),
	("rodrigo@email.pt", "Gggggggg", "05-06-2010", "Hoje pequei-me"),

	("rodrigo@email.pt", "Hhhhhhhh", "05-06-2010", "Hoje peguei-me"),
	("artur@email.pt", "Jjjjjjjjjjj", "05-06-2010", "Hoje banhei-me"),

	("faria@email.pt", "Kkkkkkkkk", "05-06-2010", "Hoje colhi-me"),
	("artur@email.pt", "Lllllllll", "05-06-2010", "Hoje tapei-me"),
]

def refresh_test (account):
	turn = account[6]
	if turn  < len (msgs)-1:
		for i in xrange (turn, turn+2):
			m = msgs[i]
			add_message (m[0], "rpmcruz", "", "", m[1], m[3], m[2])
	set_account_last_message (account[0], turn+2)

# Factory

def refresh_accounts():
	accounts = list_accounts()
	for a in accounts:
		if a[1] == "pop3":
			refresh_pop3 (a)
		else:
			refresh_test (a)

