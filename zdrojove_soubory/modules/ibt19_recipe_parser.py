"""
@project: IBT19 - xmitas02
@brief: Parsing testing and graph recipes
@author: Matej Mitas
@file: ibt19_recipe_arser.py
"""

"""
Generic library imports
"""
import os
import json
from termcolor import colored
"""
Functional imports
"""
import modules.ibt19_utils as utils

class Recipe_Parser:
	def __init__(self, path, oper_type):
		self.path = path
		self.type = oper_type
		self.know_modes = ['data', 'info', 'graph']
		self.required = {
			'tests': {
				'core': ['name', 'files', 'directory', 'drivers', 'routines'],
				'files': ['include', 'exclude'],
				'routines': ['compress', 'decompress', 'psnr']
			},
			'graph': {
				'core': ['data_session', 'description']
			}
		}
		

	def parse(self):
		"""
		Parse recipe file, used for both tests and graph
		"""
		if not os.path.isfile(self.path):
			utils.msg_error('recipe', 'Can\'t find recipe \n{}'.format(os.path.abspath(self.path)))
			return False

		with open(self.path) as json_file:
			try:
				data = json.load(json_file)
				"""
				Highest level
				"""
				base_level_keys = list(data.keys())
				base_level_keys_len = len(base_level_keys)
				if (base_level_keys_len != 1):
					if (base_level_keys_len == 0):
						utils.msg_info('recipe', 'Recipe empty')
					else:
						utils.msg_error('recipe', 'Recipe includes more than two base operations')
					return False
				
				"""
				Highest level testing
				"""
				for key_item in base_level_keys:
					if key_item not in list(self.required.keys()):
						utils.msg_error('recipe', '"{}" is not valid base operation'.format(key_item))
						return False

				"""
				Type of desired operation and recipe type must match
				"""	
				if (self.type != base_level_keys[0]):
					utils.msg_error('recipe', 'can\'t use "{}" recipe for "{}" mode'.format(base_level_keys[0], self.type))
					return False

				"""
				Test recipe
				"""
				if (self.type == 'tests'):
					for test in data['tests']:
						test_type = test['type']
						"""
						Test have two types, either approximation that do not carry final
						result and final that correspond with their name
						"""
						if test_type == 'approximation':
							test_level_keys = list(test.keys())
							test_level_keys_len = len(test_level_keys)

							if (test_level_keys_len < len(self.required['tests']['core'])):
								utils.msg_info('recipe', 'Recipe empty')

							if not os.path.isdir(test['dir']):
								utils.msg_error('recipe', 'Invalid dir path {}'.format(test['dir']))
								return False


							routines = test['routines']
							for routine in routines:
								if 'testing_param' in routines[routine]:
									testing_param = routines[routine]['testing_param']['flag']
									if testing_param in routines[routine]['params'].keys():
										utils.msg_error('recipe', 'Can\'t use "{}" as a testing and regular parameter'.format(testing_param))
										return False

							file_opts = test['files']
							is_selected = None
							for key in file_opts:
								if file_opts[key]:
									if (is_selected):
										utils.msg_error('recipe', 'Too many options selected for "files", only one allowed')
										return False
									else:
										is_selected = key

							
						elif test_type == 'final':
							pass
						else:
							utils.msg_error('recipe', 'Unknown test type {}'.format(test_type))
							return False
					
					self.data = data['tests']
				elif (self.type == 'graph'):
					self.data = data['graph']
				
			except ValueError:
				utils.msg_error('recipe', 'file corrupted of not valid \n{}'.format(os.path.abspath(self.path)))
				return False

		return True

	def get_tests(self):
		for test in self.data:
		 	yield test

	def get_graphs(self):
		for graph in self.data:
			yield graph

