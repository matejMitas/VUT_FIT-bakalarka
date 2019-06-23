"""
@project: IBT19 - xmitas02
@brief: Core of testing program
@author: Matej Mitas
@file: ibt19_tester.py
"""

"""
Generic library imports
"""
import pprint
import pickle
import subprocess
import time
import os
import cv2
import numpy
"""
Class imports
"""
from modules.ibt19_lib		  		import Lib
"""
Functional imports
"""
import modules.ibt19_defs as defs
import modules.ibt19_utils as utils

class Routine:
	def __init__(self, libs, driver, aux_files, file, criterion, testing_blueprint):
		self.compress 		= libs[defs.COMPRESS]
		self.decompress 	= libs[defs.DECOMPRESS]
		self.comparator 	= libs[defs.COMPARATOR]

		self.driver 		= driver 
		self.aux_files 		= aux_files
		self.file 			= file	
		
		self.blueprint 		= testing_blueprint
		self.testing_flag  	= testing_blueprint['flag']
		self.criterion 		= criterion

		self.scaled_file 	= utils.construct_path('scaled_file.ppm')
		self.allow_print 	= True
		"""
		Set mode in which we want to carry out tests
		'approximation'
		'final'
		"""
		self._set_mode()
		"""
		Preventing infinte loop with given criterion
		"""
		self.last_values_list = [0] * defs.PSNR_LOOP_PREVENTION_VALUES
		self.last_values_cnt = 0
		"""
		Better starting aproximations
		"""
		self.aprx = []
		



	def execute(self, allow_print=True):
		"""
		Prepare scaled file for aproximation testing
		"""
		self.allow_print = allow_print
		self._set_file('full')
		"""
		Get color mode (RGB/Gray)
		"""
		self.color_mode = utils.get_path_file(self.file)['file'].split('.')[1]
		"""
		Each test can have variants that need to examined
		"""
		start = 0.001
		end = 1


		if self.mode == defs.TEST_APRX:
			"""
			For approximations
			"""
			mean_list = []
			for variant in range(self.variants):
				"""
				Variant and variant corresponding to selected opt in
				concrete case
				"""
				self.variant = variant
				lib_variant = self.compress.get_variable_opt(self.variant)
				"""
				Initialization of record
				"""
				self._prepare_record()
				self.record['testing_opt_index'] 	= variant
				self.record['testing_opt'] 			= lib_variant
				"""
				Setting up the process
				"""
				utils.msg_test('routine', 'Selected variant: {}'.format(lib_variant))
				"""
				It's possible to have multiple values to compare againts
				"""

				for criterion in self.criterion['value']:
					if self.criterion['type'] == 'psnr':
						utils.msg_test('routine', 'Selected criterion: {}dB'.format(criterion))
						"""
						Lossless compression is selected
						"""
						if criterion == defs.CRITERION_LOSSLESS:
							self.compress.set_quality(-1)
							res = self._run_routine(lossless=True)
							self._print_routine_result(res, self.testing_flag, True)

							yield self.record

						else:
							#print(start, end)
							#print(mean_list)
							if self._find_quality(start, end, criterion):
								# print(start, end)
								utils.msg_info('used_rate', self.record['rate'])
								"""
								Store all finished rates
								"""
								self.aprx.append(self.record['rate'])
								yield self.record
							else:
								yield {}

					elif self.criterion['type'] == 'rate':
						self.compress.set_quality(criterion)
						#print(self.compress.construct(None))
						res = self._run_routine(lossless=False)
						self._print_routine_result(res, self.testing_flag, True)


						if self.blueprint['store']:
						 	self._store_test_file(criterion)

						yield self.record

				print()

		elif self.mode == defs.TEST_FINAL:
			"""
			Prepare record and set basic info
			"""
			self._prepare_record()
			self.variant = self.variant_index
			self.record['testing_opt_index'] = self.variant_index
			"""
			Match lib variant from variant index
			"""
			lib_variant = self.compress.get_variable_opt(self.variant_index)
			self.record['testing_opt'] = lib_variant
			"""
			Display type info
			"""
			utils.msg_test('routine', 'Selected variant: {}'.format(lib_variant))
			"""
			Carry out compression/decompression
			"""
			self.compress.set_quality(self.criterion['value'])
			res = self._run_routine(lossless=True)
			res['quality'] = 0
			self._print_routine_result(res, self.testing_flag, True)
			"""
			Return
			"""
			yield self.record



	def _set_mode(self):
		if 'variant_count' in self.blueprint:
			self.variants 	   	= self.blueprint['variant_count']
			self.mode 			= defs.TEST_APRX
		elif 'variant_index' in self.blueprint:
			self.variant_index 	= self.blueprint['variant_index']
			self.mode 			= defs.TEST_FINAL


	def _find_quality(self, start, end, criterion):
		start, end = self._find_interval(start, end, criterion)
		iteration_count = 0

		while True:

			interval_len = end - start
			middle = start + (interval_len / 2)

			# print('Bisection')
			# print('Middle of interval <{}, {}> is {}'.format(start, end, middle))

			self.compress.set_quality(middle)
			res = self._run_routine(lossless=False)
			"""
			Prevent infinite loop, we check last 3 values (defined in PSNR_LOOP_PREVENTION_VALUES)
			if there are same, there's not possible trend to converge 
			"""
			self._last_values_add(res['quality'])
			if len(set(self.last_values_list)) == 1:
				return False


			if (abs(criterion - res['quality']) > defs.PSNR_PRECISION):
				self._print_routine_result(res, self.testing_flag, False)

				if (res['quality'] > criterion):
					#print('<{}, {}>'.format(start, middle))
					end = middle
				else:
					#print('<{}, {}>'.format(middle, end))
					start = middle

			else:
				self._print_routine_result(res, self.testing_flag, True)
				
				"""
				If it's needed, set selected files aside for possible examination 
				"""
				if self.blueprint['store']:
					self._store_test_file(criterion)

				return True

	def _store_test_file(self, criterion):
		folder_name = '{}/{}'.format(defs.TEMP_SAVED_PATH, self.blueprint['session'])
		"""
		Create test session folder for storing selected images
		"""
		utils.check_folder_presence(folder_name)
		"""
		Prepare naming
		"""
		file_name = utils.get_path_file(self.file)['file'].split('.')[0]
		folder_file_name = '{}/{}'.format(folder_name, file_name)
		utils.check_folder_presence(folder_file_name)

		save_file_name = '{}+{}+{}.jp2'.format(self.testing_flag, self.record['testing_opt'], criterion)
		"""
		Move desired files
		"""
		os.rename(self.aux_files['compress'], '{}/{}'.format(folder_file_name, save_file_name))

	def _find_interval(self, start, end, criterion):
		interval_len = end - start

		while True:
			#utils.msg_info('test', 'Compressing')
			self.compress.set_quality(end)
			res = self._run_routine(lossless=False)

			self._print_routine_result(res, self.testing_flag, False)

			if (criterion < res['quality']):
				return [start, end]

			start = end
			end = end+interval_len



	"""
	PRIVATE
	"""
	def _last_values_add(self, value):
		if self.last_values_cnt > defs.PSNR_LOOP_PREVENTION_VALUES-1:
			self.last_values_cnt = 0

		self.last_values_list[self.last_values_cnt] = value
		self.last_values_cnt += 1

	def _gen_quality_outline(self, begin, end, samples):
		"""

		"""
		scaled_quality_intervals 	= []
		scaled_quality 				= []
		scaled_rate 				= []

		self._set_file('scaled')

		for i in numpy.linspace(begin, end, samples):
			possible_rate = round(i, 5)

			self.compress.set_quality(possible_rate)
			res = self._run_routine()

			scaled_rate.append(res['rate'])
			scaled_quality.append(res['quality'])

			#self._print_routine_result(res, self.testing_flag, False)

		"""
		Convert to intervals
		"""
		for i in range(0, len(scaled_quality) - 1):
			scaled_quality_intervals.append((scaled_quality[i], scaled_quality[i+1]))

		return [scaled_quality_intervals, scaled_rate]


	def _match_in_interval(self, tup, value):
		for it, tup in enumerate(tup):
			min = tup[0]
			max = tup[1]

			if value >= min and value <= max:
				diff_min = max - value
				diff_max = value - min

				if (diff_min > diff_max):
					return it
				else:
					return it+1


	def _set_file(self, file_type):
		"""
		Routine takes implicit file name defined on Class basis
		so we need to have a tool to change it to our liking
		"""
		if (file_type == 'full'):
			file = self.file
		elif (file_type == 'scaled'):
			file = self.scaled_file

		self.compress.set_input(file)
		self.comparator.set_input(file)


	def _run_routine(self, lossless):
		"""
		Compression
		"""
		cmd = self.compress.construct(self.variant)
		#print(" ".join(cmd))
		elapsed_compression = self._invoke(cmd)
		if elapsed_compression == -1:
			return False
		
		memory_compression = self._memory()
		"""
		Decompression, separate output file needs to be set because 
		single channel files are saved to separate file
		"""
		if self.color_mode == 'pgm':
			self.decompress.set_output(self.aux_files['decompress_low'])
			self.comparator.set_output(self.aux_files['decompress_low'])

		cmd = self.decompress.construct(None)
		elapsed_decompression = self._invoke(cmd)
		if elapsed_decompression == -1:
			return False
		memory_decompression = self._memory()
		"""
		Criterion comparison
		"""
		if not lossless:
			cmd = self.comparator.construct(None)
			elapsed_comparator = self._invoke(cmd)
			comparator = round(self._compare(), 2)
			if elapsed_comparator == -1:
				return False
		else:
			comparator = defs.CRITERION_LOSSLESS
		"""
		Record to store in database
		"""
		self.record['compression'] = {
			'time'		: elapsed_compression,
			'memory'	: memory_compression
		}
		self.record['decompression'] = {
			'time'		: elapsed_decompression,
			'memory'	: memory_decompression
		}
		self.record['quality'] = comparator
		self.record['size'] = self._size()
		self.record['rate'] = self.compress.get_quality()
		"""
		Return for testing purposes
		"""
		return {
		 	'compression'	: elapsed_compression,
			'decompression'	: elapsed_decompression,
			'quality'		: comparator,
			'rate'			: self.record['rate']
		}
	

	def _print_routine_result(self, payload, testing_flag, is_final):
		"""
		Print out iteration test
		"""
		if self.allow_print:
			utils.msg_done('{}'.format(testing_flag), '', no_newline=True)
			print('{:02f}s | {:02f}s |'.format(payload['compression'], payload['decompression']), end='')
			utils.msg_compare(payload['quality'], is_final)

	def _invoke(self, flags):
		return utils.invoke_process(flags, self.aux_files['stdout'], self.aux_files['stderr'], True)

	def _memory(self):
		return 1
		#return utils.get_memory_usage(self.aux_files['stdout'])

	def _compare(self):
		return utils.get_psnr(self.aux_files['stdout'])

	def _size(self):
		self._invoke(['wc', '-c', self.aux_files['compress']])
		with open(utils.construct_path(self.aux_files['stderr']), "r") as data:
			return int(data.read().lstrip().split(' ')[0]) * 8

	"""
	PREPARED
	"""
	def _prepare_scaled_file(self):
		"""
		Prepared scaled file for aproximation testing
		"""
		elapsed_scaled = self._invoke(['convert', self.file, '-resize', '10%',  self.scaled_file])
		utils.msg_test('routine', 'Generated small file for comparision ({}s)'.format(round(elapsed_scaled, 4)))

	def _prepare_record(self):
		self.record = {
			'driver'		: self.driver,
			'testing_flag'	: self.testing_flag,
			'testing_opt'	: None,
			'compression'	: {
				'time'		: 0,
				'memory'	: 0,
			},
			'decompression'	: {
				'time'		: 0,
				'memory'	: 0
			},
			'quality'		: 0
		}