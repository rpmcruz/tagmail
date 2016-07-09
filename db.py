# db.py

import os, sys
from pysqlite2 import dbapi2 as sqlite
from utils import *
from ui_utils import *

singleton = None

def get_db():
	global singleton
	if singleton == None:
		singleton = Db()
	return singleton

class Db:
	def __init__(self):
		filename = os.path.join (os.path.expanduser('~'), ".tagmail")
		exists = os.path.exists (filename)
		try:
			self.conn = sqlite.connect (filename, timeout = 0.5)
			self.cur = self.conn.cursor()
		except sqlite.OperationalError, error:
			error_msg ("SQL error", "Could not load db file: " + filename + "\n" + str (error))
			sys.exit (-1)

		if not exists:
			self.cur.execute ("""
				create table MESSAGES (ID integer primary key,
					_FROM text, _TO text, CC text, MAILING_LIST text,
					SUBJECT text, CONTENT text, DATE text, MARK_READ int)
				""")
			self.cur.execute ("""
				create table EMAILS (VALUE text primary key,
					NAME text, FAVORITE int)
				""")
			self.cur.execute ("""
				create table MAILING_LISTS (VALUE text primary key,
					NAME text, FAVORITE int)
				""")
			self.cur.execute ("""
				create table ACCOUNTS (ID integer primary key,
					TYPE text, SERVER text, USERNAME text,
					PASSWORD text, PROTOCOL text, LAST_MSG int)
				""")
			self.conn.commit()

# Accounts

def add_account (type, server, username, password, protocol):
	db = get_db()
	db.cur.execute ("insert into ACCOUNTS values (null,?,?,?,?,?,?)",
		(type, server, username, password, protocol, 1))
	db.conn.commit()

def remove_account (id):
	db = get_db()
	db.cur.execute ("delete from ACCOUNTS where ID=?", (id,))
	db.conn.commit()

def list_accounts():
	db = get_db()
	db.cur.execute ("select * from ACCOUNTS")
	return db.cur.fetchall()

def set_account_last_message (id, last_msg):
	db = get_db()
	db.cur.execute ("update ACCOUNTS set LAST_MSG=? where ID=?", (last_msg, id,))
	db.conn.commit()

# Abstracts attributes

def parse_email (s):  # returns (name, email)
	name = ""
	email = s

	# email parse
	i = s.find ('<')
	if i != -1:
		j = s.find ('>')
		if j != -1:
			email = s[i+1:j]

		# name parse
		j = s.find ('"')
		k = -1
		if j != -1:
			k = s[j+1:].find ('"')
		if j != -1 and k != -1:
			name = s[j+1:k+1]
		else:
			name = s[:i]
		name.strip()
	return (name, email)

def add_attrb (table, value, name):
	db = get_db()
	db.cur.execute ("select * from %s where VALUE=?" % table, (value,))
	if db.cur.fetchone() == None:
		db.cur.execute ("insert into %s values (?,?,?)" % table, (value, name, 0))
		db.conn.commit()

def list_attrb (table):
	db = get_db()
	# order by FAVORITE desc, VALUE   # order at ui level
	db.cur.execute ("select * from %s" % table)
	return db.cur.fetchall()

def is_favorite_attrb (table, value):
	db = get_db()
	db.cur.execute ("select FAVORITE from %s where VALUE=?" % table, (value,))
	return bool (db.cur.fetchone()[0])

def favorite_attrb (table, value, favorite):
	db = get_db()
	fav = int (favorite)
	db.cur.execute ("update %s set FAVORITE=? where VALUE=?" % (table), (fav, value))
	db.conn.commit()

def name_attrb (table, value, name):
	db = get_db()
	db.cur.execute ("update %s set NAME=? where VALUE=?" % (table), (name, value))
	db.conn.commit()

def add_filter (filter, var, value, op):
	if value == None or value == "":
		return filter
	if filter == "":
		filter = "where "
	else:
		filter += "and "
	filter += "%s%s'%s'" % (var, op, value)
	return filter

def count_attrb (attrb, value):
	db = get_db()
	db.cur.execute ("select count(%s) from MESSAGES where %s=?" % (attrb, attrb), (value,))
	total_count = db.cur.fetchone()[0]
	db.cur.execute ("select count(%s) from MESSAGES where %s=? and MARK_READ=0" % (attrb, attrb), (value,))
	new_count = db.cur.fetchone()[0]
	return (total_count, new_count)

def count_messages():
	db = get_db()
	db.cur.execute ("select count(ID) from MESSAGES")
	total_count = db.cur.fetchone()[0]
	db.cur.execute ("select count(ID) from MESSAGES where MARK_READ=0")
	new_count = db.cur.fetchone()[0]
	return (total_count, new_count)

# Emails

def list_emails():
	return list_attrb ("EMAILS")

def favorite_email (value, favorite):
	favorite_attrb ("EMAILS", value, favorite)

def count_email_messages (value):
	count_attrb ("EMAIL", value)

# Mailing lists

def list_mailing_lists():
	return list_attrb ("MAILING_LISTS")

def favorite_mailing_list (value, favorite):
	favorite_attrb ("MAILING_LISTS", value, favorite)

def count_mailing_list_messages (value):
	count_attrb ("MAILING_LIST", value)

# Messages

def add_message (_from, to, cc, mailing_list, subject, content, date):
	db = get_db()
	try:
		_from, _from_v = parse_email (_from)
		mailing_list, mailing_list_v = parse_email (mailing_list)

		db.cur.execute ("insert into MESSAGES values (null,?,?,?,?,?,?,?,?)",
			(_from_v, to, cc, mailing_list_v, subject, content, date, 0))
		db.conn.commit()

		add_attrb ("EMAILS", _from_v, _from)
		add_attrb ("MAILING_LISTS", mailing_list_v, mailing_list)
	except sqlite.OperationalError, error:
		print "SQL Error: Could not add message:", subject
	except sqlite.ProgrammingError, error:
		print "SQL Error: Could not add message:", subject

def list_messages (search, email, mailing_list):
	db = get_db()
	# TODO: search (use 'like' ?)
	filter = add_filter ("", "_FROM", email, "=")
	filter = add_filter (filter, "MAILING_LIST", mailing_list, "=")
	db.cur.execute ("select * from MESSAGES %s" % filter)
	return db.cur.fetchall()

def select_message (id):
	db = get_db()
	db.cur.execute ("select * from MESSAGES where ID=?", (id,))
	return db.cur.fetchone()

def mark_message_as_read (id):
	db = get_db()
	db.cur.execute ("update MESSAGES set MARK_READ=1 where ID=?", (id,))
	db.conn.commit()

def mark_all_message_as_read():
	db = get_db()
	db.cur.execute ("update MESSAGES set MARK_READ=1")
	db.conn.commit()

