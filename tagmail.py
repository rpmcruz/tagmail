#!/usr/bin/python

import sys
try: import gtk
except:
	print "Error: GTK not installed."
	sys.exit (-1)

from ui import *

try: import pysqlite2.dbapi2
except: fatal_error ("python-pysqlite2 not installed")

if __name__ == "__main__":
	ui = MainUI()
	ui.run()

