"""
Main file
@project: IBT19 - xmitas02
@brief: Main file
@author: Matej Mitas
@file: ibt19_entry.py
"""

"""
Generic library imports
"""
import cv2
import os
import sys
import numpy
import time
import subprocess
import configparser
"""
Class imports
"""
from modules.ibt19_args 			import Args
from modules.ibt19_dir_scanner 		import Dir_Scanner
from modules.ibt19_database 		import Database
from modules.ibt19_recipe_parser 	import Recipe_Parser
from modules.ibt19_tester			import Tester
from modules.ibt19_graph_draw		import Graph_Draw
"""
Functional imports
"""
import modules.ibt19_defs as defs
import modules.ibt19_utils as utils

class Program():
	def __init__(self):
		"""
		Commandline argument parsing
		"""
		self.args = Args().parse_args()
		if (self.args == None):
			return 
		"""
		Program init
		"""
		utils.msg_welcome()
		if not utils.check_libraries():
			utils.msg_error('check', 'CAN\'T LAUNCH')
			return
		"""
		Database handling, crutial for program execution
		"""
		config = configparser.ConfigParser()
		config.read('config/ibt19_db.ini')
		self.db = Database(config['DB'])
		if not self.db.check_connection():
			utils.msg_error('database', 'can\'t connect to database')
			return 
		"""
		One of three modes program can run in
		1: Checking directory
		2: Test execution according to the recipe
		3: Graph drawing 
		"""
		getattr(self, 'execute_{}'.format(self.args['type']))()
	
	def execute_check(self):
		"""
		In order to carry out tests we need to know inside given directory
	    """
		scanner = Dir_Scanner(self.args['path'], self.db, defs.PPM_REGEX)
		data = scanner.scan()

	def execute_tests(self):
		last_session_hash = None
		"""
		Core method of whole program, execute test
	    """
		if self._load_recipe('tests'):
			for test in self.parser.get_tests():
				"""
				Approximation test followed by final test
				"""
				if last_session_hash:
					test['source'] = last_session_hash
					#print(test['source'])
				"""
				Approximation test get its hash stored for upcoming
				final test
				"""
				possible_session = Tester(test, self.db).execute()
				if possible_session:
					last_session_hash = possible_session


	def execute_graph(self):
		"""
		Display data in clear way
    	"""
		if self._load_recipe('graph'):
			for graph in self.parser.get_graphs():
				Graph_Draw(graph, self.db).execute()

	"""
	PRIVATE
	"""
	def _load_recipe(self, recipe_type):
		self.parser = Recipe_Parser(self.args['path'], recipe_type)
		if not self.parser.parse():
			return False
		return True		

my_prg = Program()