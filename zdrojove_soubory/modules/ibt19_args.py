"""
@project: IBT19 - xmitas02
@brief: Commandline arguments
@author: Matej Mitas
@file: ibt19_args.py
"""

"""
Generic library imports
"""
import argparse
import os
"""
Functional imports
"""
import modules.ibt19_utils as utils

defs = {
	'NOLOG' 	: 'nolog',
	'TESTS'		: 'tests',
	'CHECK'		: 'check',
	'GRAPH'		: 'graph'
}

class Args:
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description='IBT19. Bachelor thesis \'Analýza nastavení formátu JPEG 2000\', see below'
		)
		self.parser.add_argument('-t', '--tests', metavar='', help='Run tests')
		self.parser.add_argument('-c', '--check', metavar='', help='Check directory')
		self.parser.add_argument('-g', '--graph', metavar='', help='Display graph')

		self.parser.add_argument('-n', '--nolog', action='store_true')
		self.parser.add_argument('-o1', '--optm1', action='store_true')

		self.args = self.parser.parse_args()

	"""
	Multiple possible modes, can disable logging to database
	"""
	def parse_args(self):
		mode = {
			'type'	: None,
			'path'	: None,
			'log'	: not self.args.nolog	
		}

		for arg in vars(self.args):
			path = getattr(self.args, arg)
			if (arg != defs.get('NOLOG')):
				if (path):
					if (mode['type']): 
						utils.msg_error('args', 'Can\'t combine arguments, see help for more information')
						return None
					else:
						mode['type'] = arg
						"""
						Full path required with subsequent fetching
						"""
						mode['path'] = os.path.abspath(path)

		if (mode['type'] == None):
			utils.msg_error('args', 'Must use at least one option, see help for more information')
		else:
			return mode
