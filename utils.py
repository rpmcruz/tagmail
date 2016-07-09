# path.py

import os

class TagException (Exception):
	def __init__ (self, title, details):
		self.title = title
		self.details = details

	def __str__ (self):
		return self.title

