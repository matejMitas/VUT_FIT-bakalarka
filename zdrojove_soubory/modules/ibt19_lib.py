"""
@project: IBT19 - xmitas02
@brief: Abstraction over libraries
@author: Matej Mitas
@file: ibt19_lib.py
"""

"""
Generic library imports
"""
from functools import reduce
import os
import json
"""
Functional imports
"""
import modules.ibt19_defs as defs
import modules.ibt19_utils as utils

class Lib:
	def __init__(self):
		self.config_path = 'config/flags_config.json'
		self.program_indexes = list(defs.LIBS.values())

		self.opt_match_table = {
			'single'		: '{}',
			'pair'			: '{},{}',
			'pair_braces'	: '{{{},{}}}',
			'pair_box'		: '[{},{}]'
		}

	def set_file_info(self, info):
		info = info['ctx']
		self.file_info = {
			'width'			: info['dims']['width'],
			'height'		: info['dims']['height'],
			'size'			: info['size'],
			'color_depth'	: 0
		}

	def set_input(self, input_file):
		"""
		Used for compression, otherwise working with temp files.
		"""
		self.flags['base']['input'] = input_file

	def set_output(self, output_file):
		"""
		Used when changing from 24RGB (PPM) to 8 (PGM)
		"""
		self.flags['base']['output'] = output_file

	def set_quality(self, quality):
		self.flags['variable']['quality'] = quality

	def get_quality(self):
		return self.flags['variable']['quality']

	def prepare_lib(self):
		with open(self.config_path) as json_file:
			try:
				self.flags_match_table = json.load(json_file)
				return True
			except ValueError as e:
				utils.msg_error('internal', 'config file corrupted of not valid \n{}'.format(os.path.abspath(self.config_path)))
				utils.msg_error('internal', e)
				return False

	def get_variable_opt(self, index):
		testing_list = self.flags['variable']['testing_blueprint']
		if index == -1:
			return testing_list
		else:
			return testing_list[index]

	"""
	Program and I/O params, used for resetting, use wisely
	"""
	def prepare_base(self, driver, file_flags, input_file, out_file):
		self._flush_all_flags()

		self.flags['base'] = { 
			'driver'		: driver,
			'driver_type'	: self.program_indexes.index(driver),
			'input'			: input_file,
			'output'		: out_file,
			'file_flags'	: file_flags
		}

	def prepare_fixed(self, flags):
		self.dest = self.flags['fixed']
		for flag in flags:
			self.curr_flag = self._match(flag)
			"""
			Is there anything to match. We need to deconstruct passed options,
			so they are structured according to the blueprint.
			"""
			if self.curr_flag and len(self.curr_flag):
				self._transform_flag(flags[flag])

	def construct(self, variant_index):
		prepared_flags = []
		"""
		Get base information, print it out to the buffer, 
		"""
		base = self.flags['base']
		fixed = self.flags['fixed']
		variable = self.flags['variable']
		# driver
		self._append(prepared_flags, base['driver'])
		# base arguments
		prepared_base = ('-i', base['input'], '-o', base['output']) if base['file_flags'] else (base['input'], base['output'])
		self._append(prepared_flags, *prepared_base)
		"""
		Pre-set params defined in 'params'
		"""
		prepared_flags += fixed
		"""
		Variable params, corresponds to 'testing_param'
		"""
		if variant_index != None:
			"""
			Some flags like mode might have a test variant without explicitly
			turn on flag with parameters, might just be without it
			"""
			variable_opt = variable['testing'][variant_index]
			if variable_opt:
				prepared_flags += variable_opt


			compression_flag = []
			self.dest =	compression_flag
			self.curr_flag = self._match('compression')
			"""
			Multiple calling of same flags does not reflect
			on setting up for next steps so we need to toogle it
			back to original state
			"""
			try:
				self.flags['base']['driver'].index('kdu')
				self.curr_flag['format'] = 'match'
			except ValueError:
				self.curr_flag['format'] = 'toggle'
			"""
			Using lossless setting
			"""
			if variable['quality'] != -1:
				self._transform_flag("lossy")
				"""
				Handle quality
				"""
				quality_flag = []
				self.dest = quality_flag
				self.curr_flag = self._match('quality')
				self._transform_flag([variable['quality']])

				prepared_flags += quality_flag
			else:
				"""
				Simple set lossless
				"""
				self._transform_flag("lossless")
			"""
			Add compression flag according to quality
			"""
			prepared_flags += compression_flag
		
		return prepared_flags



	def prepare_testing(self, flag):
		"""
		Create basic 
		"""
		if flag:
			prepared_count = 0
			self.curr_flag = self._match(flag['flag'])
			"""
			We can either list all options or use 'range' shortcut
			"""
			if 'range' in flag:
				"""
				We need to make sure we have correct range
				"""
				start = min(flag['range'])
				if start < 0:
					utils.msg_error('recipe', 'You can\'t use negative number as range.')
					return False
				end = max(flag['range'])
				"""
				Normalisation for range
				"""
				for i in range(start, end + 1):
					temp_buffer = []
					self.dest = temp_buffer
					"""
					If we have certain modifier for counter
					"""
					if ('step' in flag):
						if (flag['step'] == '2n'):
							i = 2**i
					"""
					We need to format 'opt' for upcoming usage
					"""
					if (self.curr_flag['format'].find('pair') != -1):
						self._transform_flag([i,i])
					else:
						self._transform_flag(i)


					self._append(self.flags['variable']['testing_blueprint'], i)
					self._append(self.flags['variable']['testing'], temp_buffer)
					prepared_count += 1
			else:
				"""
				We don't normally call 'self._transform_flag()' without refreshing
				'self.curr_flag' but here it creates mutual overriding so hotfix is
				to back it up
				"""
				format_backup = self.curr_flag['format']
				for opt in flag['opts']:
					temp_buffer = []
					self.dest = temp_buffer

					if opt != None:
						self._transform_flag(opt)
						self.curr_flag['format'] = format_backup

						self._append(self.flags['variable']['testing'], temp_buffer)
						self._append(self.flags['variable']['testing_blueprint'], opt)
					else:
						self._append(self.flags['variable']['testing'], None)
						self._append(self.flags['variable']['testing_blueprint'], False)

					prepared_count += 1
			return prepared_count
	"""
	PRIVATE
	"""
	def _transform_flag(self, opts):
		"""
		Carry out matching before asigning
		"""
		if self.curr_flag['format'] == 'match':
			"""
			Single match from two member list or multiple values matching
			with optional modifier
			"""
			if ('modifier' in self.curr_flag):
				mod = self.curr_flag['modifier']
				matched_values = []
				for opt in opts:
					matched_values.append(self.curr_flag['match_pattern'][opt])

				if (self.curr_flag['modifier'] == '+'):
					opts = reduce((lambda x, y: x + y), matched_values)
			else:
				opts = self.curr_flag['match_pattern'][opts]
			"""
			Treat as normal single options afterwards
			"""
			self.curr_flag['format'] = 'single'
		else:
			if ('modifier' in self.curr_flag):
				mod = self.curr_flag['modifier']
				if (mod == 'rate'):
					temp_opts = []
					"""
					There is not particular need to use actual file dimensions.
					Compression rate can be calculated artifically. But since data
					are already assigned it make sense to use them
					"""
					for opt in opts:
						dims = self.file_info['width'] * self.file_info['height']
						temp_opts.append((dims * 24) / (dims * float(opt)))

					opts = temp_opts

		"""
		Check if params are correct type
		"""
		if 'list' in self.curr_flag:
			"""
			First we begin as usual but we don't print out flag but store it in
			'list_buffer', then is being filled with other options.
			Lastly we flush out the buffer
			"""
			if (len(opts)):
				self._assign(opts[0], is_list=False, is_start=True)
				for opt in opts[1:]:
				 	self._assign(opt, is_list=True, is_start=False)
				self._append(self.dest, self.settings['list_buffer'])
				self._clear_buffer()
		else:
			self._assign(opts, is_list=False, is_start=False)	

	def _assign(self, opt, is_list, is_start):
		dest = self.dest
		flag = self.curr_flag
		"""
		We need to do some matching because either libraries
		differ or more advanced options are provided and can't
		be simple inserted
		"""
		if flag['format'] == 'toggle':
			"""
			We want to add flag based on generic option
			Also possible to use toggle based on boolean values 
			rather than expliciting option listing
			"""
			to_append = flag['opt']

			if ('toggle_pattern' in flag):
				if flag['toggle_pattern'][opt]:
			 		self._append(dest, to_append)
			else:
				if opt:
					self._append(dest, to_append)

		else:
			if type(opt) == list:
				opt = self.opt_match_table[flag['format']].format(*opt)
			else:
				opt = self.opt_match_table[flag['format']].format(opt)
			"""
			First we adress list item, nothing fancy, just add it
			to the buffer
			"""
			if (is_list):
				self._add_to_buffer('{}{}'.format(flag['list']['divider'], opt))
			else:
				"""
				Main difference between libraries, format business
				"""
				if (flag['divider'] == '='):
					prepared_opt = '{}{}{}'.format(flag['opt'], flag['divider'], opt)
				else:
					self._append(dest, flag['opt'])
					prepared_opt = '{}'.format(opt)
				"""
				Is there is a list, first item need to correspond with 
				previously set format
				"""
				if (is_start):
					self._add_to_buffer(prepared_opt)
				else:
					self._append(dest, prepared_opt)


	def _flush_all_flags(self):
		"""
		Initialize basic working structure.
		'testing_blueprint' used mainly for debugging purposes
		"""
		self.flags = {
			'base'		: {
				'driver'		: None,
				'driver_index'	: -1,
				'input'			: None,
				'output'		: None,
				'file_flags'	: False
			},
			'fixed' 	: [],
			'variable' 	: {
				'testing'			: [],
				'testing_blueprint'	: [],
				'quality'			: 0
			}
		}

		self.settings = {
			'file_flags' 	: None,
			'driver_type'	: None,
			'list_buffer' 	: ''
		}

		self.file_info = {
			'width'			: 0,
			'height'		: 0, 
			'size'			: 0,
			'color_depth'	: 0
		}


	def _add_to_buffer(self, item):
		"""
		Insert into buffer used for list flag processing
		"""
		self.settings['list_buffer'] += item

	def _clear_buffer(self):
		"""
		Clear buffer for list flag processing
		"""
		self.settings['list_buffer'] = ''			

	def _match(self, flag):
		"""
		Match possible flag from table, others will get discarted
		"""
		if flag in self.flags_match_table:
			try:
				return self.flags_match_table[flag][self.flags['base']['driver_type']]
			except IndexError:
				return []
		else:
			return []

	def _append(self, insert_to, *args):
		for arg in args:
			if type(arg) == list and not len(arg):
				return
			else:
				insert_to.append(arg)
