"""
@project: IBT19 - xmitas02
@brief: Main testing module
@author: Matej Mitas
@file: ibt19_tester.py
"""

"""
Generic library imports
"""
from pprint import pprint
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
from modules.itb19_routine		  	import Routine
"""
Functional imports
"""
import modules.ibt19_defs as defs
import modules.ibt19_utils as utils

class Tester:
	def __init__(self, config, db):
		self.db 		= db
		self.config 	= config
		self.mode = config['type']

		self._prepare_tester()

	"""
	PUBLIC
	"""
	def execute(self):
		"""
		Entering point of a single test fetched from recipe file. Main wrapper and controlling
		element of complete test run (compress, decompress, setting parameters according to criterion) 
		"""
		if self._prepare_libs():
			"""
			Groundwork before actual tests
			"""
			self._prepare_session_record()
			self._prepare_aux_files()
			self._prepare_file_match_table()
			self._prepare_comparator()
			utils.msg_session_start(self.config['name'], self.session['hash'])
			"""
		  	Loop through routines then take each variant (driver) and loop over files
			"""
			if self.mode == defs.TEST_APRX:
				if not self._check_dir_info():
					return

			"""
			Logic
			"""
			test_ok = True
			for driver in self.config['drivers']:
			 	test_ok = self._execute_routine_pipeline(driver)
			"""
			Doesn't make sense to delete aux files containing more info about
			error after failed session
			"""
			if test_ok:
				utils.clear_aux_files()


			self.session['stamps']['end'] = utils.create_timestamp()
			self._store(defs.DB_TEST_SESSIONS, self.session)
			
			utils.msg_session_end(self.config['name'], self.session['hash'])
			print()
			return self.session['hash']

	"""
	PRIVATE
	"""
	def _execute_routine_pipeline(self, driver):
		"""
		Providing general interface for testing pipeline.
		"""		
		blueprints 		= {}
		variant_count 	= 0
		criterion 		= []

		testing_data = {
			'flag'			: None,
			'session'		: self.session['hash']
		} 

		"""
		Prepare libraries, init files
		"""
		for routine in self.routines:
			blueprints[routine] = self.routines[routine]
			lib = self.libs[routine]
			"""
			Prepare base flags.
			"""
			driver_process = defs.LIBS['{}_{}'.format(driver, routine)]
			input_file = self.file_match_table['{}_input'.format(routine)]
			output_file = self.file_match_table['{}_output'.format(routine)]
			"""
			Fill in base flags and insert fixed flags for each routine.
			"""
			lib.prepare_base(driver_process, True, input_file, output_file)
			lib.prepare_fixed(blueprints[routine]['params'])	
			"""
			If there is particular parametr that gets examined
			"""
			if 'testing_param' in blueprints[routine]:
				variant_count = lib.prepare_testing(blueprints[routine]['testing_param'])
				if not variant_count:
					return 

				testing_data['flag'] = blueprints[routine]['testing_param']['flag']
				"""
				This enables us to loop through all possible variants but when
				testing 'final', there's no need to store all variants, only one
				given for particular test
				"""
				if self.mode == defs.TEST_APRX:
					testing_data['variant_count'] = variant_count

				self.session['ctx']['opts'] = self.libs[defs.COMPRESS].get_variable_opt(-1)
				"""
				Determine whenever is there anything we can compare are
				results to
				"""
				criterion = blueprints[routine]['criterion']

		"""
		Both modes require different approach to file handling
		"""
		return getattr(self, '_execute_routine_{}'.format(self.mode))(driver, criterion, testing_data)



	def _execute_routine_approximation(self, driver, criterion, testing_data):
		file_types = []
		
		for file in self._get_dir_iterator():
			utils.msg_info(driver, file)
			"""
			Fetch info about this file. We want latest occurence to ensure actualness
			"""
			file_info = self._prepare_file_test(driver, file)
			if not file_info:
				return
			"""
			Prepare information about file to add to the record
			"""
			temp_file_info 		= file_info['ctx']
			prepared_file_info 	= {
			 	'type'	: temp_file_info['file'].split('_')[0],
			 	'name'	: temp_file_info['file'],
			 	'path'	: temp_file_info['path']
			}

			if not (prepared_file_info['type'] in file_types):
				file_types.append(prepared_file_info['type'])
			"""
			Determine if there is special need to save testing files separetely
			"""
			if prepared_file_info['name'] in self.config['to_save']:
				testing_data['store'] = True
			else:
				testing_data['store'] = False
			"""
			Run routine for each variant of testing param.
			Get raw param to display and graph
			"""
			routine = Routine(self.libs, driver, self.aux_files, file, criterion, testing_data)
			for result in routine.execute(True):
				if result == {}:
					pass
					#utils.msg_error('routine', '{} \nFile can\'t be compressed with given precision.\nMost likely not enough resolution causing peaks in criterion'.format(file))
				else:
					#print(result)
					"""
					Update with additional information. There's no need to pass
					to 'routine' object even though creation would but cleaner but more 
					overhead in terms of time and memory would be needed
					"""
					result['file'] 		= prepared_file_info
					used_rate = result['rate']

					result['rate'] = {
						'used'			: used_rate,
						'calculated'	: result['size'] / (file_info['ctx']['dims']['width'] * file_info['ctx']['dims']['height'])
					}
					"""
					Store finished record to database
					"""
					self._execute_routine_result(file, result)


		self.session['ctx']['file_types'] = file_types
		return True

	def _execute_routine_final(self, driver, criterion, testing_data):

		#print(self.libs['compress'].construct(None))
		#print(self.libs['decompress'].construct(None))

		"""
		We only need access to the database
		"""
		for item in self.db.get_many(defs.DB_TEST_DATA, {
				'ctx.driver': driver, 
				'session': self.config['source']}, {'ctx': 1, '_id': 0}):

			item = item['ctx']
			self._prepare_file_test(driver, '{}/{}'.format(item['file']['path'], item['file']['name']))
			"""
			PSNR matching, discarding possible peaks in tolerance
			"""
			rectified_quality = self._justify_criterion_value(item['quality'])
			if rectified_quality:
				item['quality'] = rectified_quality

			file = '{}/{}'.format(item['file']['path'], item['file']['name'])
			rate_to_test = item['rate']['used']
			"""
			Print out info
			"""
			utils.msg_info(driver, file)
			# utils.msg_info('rate', rate_to_test)
			# utils.msg_info('opt', item['testing_opt_index'])
			"""
			Prepare data for routine
			"""
			criterion = {
				'type': 'rate',
				'value': rate_to_test
			}
			testing_data['variant_index'] = item['testing_opt_index']
			"""
			Set up routine
			"""
			routine = Routine(self.libs, driver, self.aux_files, file, criterion, testing_data)
			"""
			Prepare items for repeated testing
			"""
			compression_data 	= []
			decompression_data 	= []

			for i in range(0,defs.REPETITON_COUNT):
				res = next(routine.execute(allow_print=False))
				compression_data.append(res['compression'])
				decompression_data.append(res['decompression'])

			"""
 			Set session result
 			"""
			item['compression'] 	= self._aprx_test_values(compression_data)
			item['decompression'] 	= self._aprx_test_values(decompression_data)
			"""
			Pack record and save it to the database
			"""
			self._execute_routine_result(file, item)
			print()

		return True


	def _execute_routine_result(self, file, result):
		test_timestamp = utils.create_timestamp()
		ret = {
			'hash'		: utils.create_hash(file, test_timestamp),
			'session'	: self.session['hash'],
			'type'		: self.mode,
			'timestamp'	: test_timestamp,
			'ctx'		: result
		}

		self._store(defs.DB_TEST_DATA, ret)
		#print(ret)

	def _justify_criterion_value(self, real_quality):
		"""
		PSNR is always measured with certain precision, but we want concrete
		values in graphs so adjusment needs to be done
		"""
		possible_criterion = self.session['ctx']['compress']['criterion']
		if possible_criterion['type'] == 'psnr':
			values = possible_criterion['value']

			if real_quality in values:
				return real_quality
			else:
				new_values = [abs(value - real_quality) for value in values]
				return values[new_values.index(min(new_values))]
		return False

	def _aprx_test_values(self, values):
		time 	= []
		memory 	= []

		for value in values:
			time.append(value['time'])
			memory.append(value['memory'])

		return {
			'time'		: numpy.average(time),
			'memory'	: numpy.average(memory)
		}

	"""
	PREPARE
	"""		
	def _prepare_tester(self):
		if self.mode == defs.TEST_APRX:
			"""
			Multiple properties need to assigned for correct function
			"""
			self.routines 	= self.config['routines']
			self.file_opts 	= self.config['files']
			self.dir 		= self.config['dir']

			print()

		elif self.mode == defs.TEST_FINAL:
			"""
			We need to portray recipe's role. By fetching aproximation data session we first supply
			mandatory 'drivers' data
			"""
			self.fetched_aprx_session = self.db.get(defs.DB_TEST_SESSIONS, {'hash': self.config['source']}, None)
			self.config['drivers'] = self.fetched_aprx_session['drivers']
			"""
			Then we add 'routines' so we can generate libraries
			"""
			compress = self.fetched_aprx_session['ctx']['compress']
			decompress = self.fetched_aprx_session['ctx']['decompress']
			"""
			Explicitly set number of threads used, very important for 
			final test in terms of time took to compress/decompress
			"""
			# compress['params']['threads'] = 1
			# decompress['params']['threads'] = 1
			"""
			Store it as if it was 'approximation' test
			""" 
			self.routines = {
				'compress'		: compress,
				'decompress'	: decompress
			}


	def _prepare_comparator(self):
		"""
		Comparator does not require any type of fancy params matching or setting
		but we are still going to use 'Lib' so that we keep things organised 
		"""
		input_file = self.file_match_table['{}_input'.format(defs.COMPARATOR)]
		output_file = self.file_match_table['{}_output'.format(defs.COMPARATOR)]

		self.libs[defs.COMPARATOR].prepare_base(defs.LIBS[defs.COMPARATOR], False, input_file, output_file)

	def _prepare_file_test(self, driver, file):
		"""
		For every test we need to find infomation about file - most notable dimensions and 
		color depth for calculation compression ratio/bpp
		"""
		db = self.db.expose(defs.DB_DIR_DATA)
		file_id = utils.get_path_file(file)
		find_params = {'ctx.file': file_id['file'], 'ctx.path': file_id['path']}

		try:
			file_info = db.find(find_params, {'_id': 0}).sort('timestamp', -1).limit(1)[0]
			self.libs[defs.COMPRESS].set_file_info(file_info)
			return file_info
		except IndexError:
			utils.msg_error('file', 'Can\'t find information about file.\n"{}"'.format(file))
			return False

	def _prepare_session_record(self):
		"""
		Create a record describing session that gets stored into database.
		"""
		timestamp = utils.create_timestamp()

		self.session = {
			'name'					: self.config['name'],
			'hash'					: utils.create_hash(self.config['name'], timestamp),
			'type'					: self.mode,
			'drivers'				: self.config['drivers'],
			'stamps'				: {
				'start'				: timestamp,
				'end'				: 0
			},
			'ctx': {
				'opts'					: [],
				'file_types'			: [],
	 			'compress'				: self.routines['compress'],
		 		'decompress'			: self.routines['decompress'],
			}
		}
		"""
		Copy file types and opts from 'approximation session', no need to get them separately
		"""
		if self.mode == defs.TEST_FINAL:
			self.session['ctx']['file_types'] 	= self.fetched_aprx_session['ctx']['file_types']
			self.session['ctx']['opts'] 		= self.fetched_aprx_session['ctx']['opts']

	def _prepare_aux_files(self):
		"""
		Create (paths to) files used as a helping containers for process execution
		or holding temporary (de)compress files.
		"""
		session_hash = self.session['hash']
		self.aux_files = {
			'compress'		: utils.construct_path('compress_{}.jp2'.format(session_hash)),
			'decompress'	: utils.construct_path('decompress_{}.ppm'.format(session_hash)),
			'decompress_low': utils.construct_path('decompress_{}.pgm'.format(session_hash)),
			'stdout'		: 'stdout_{}'.format(session_hash),
			'stderr'		: 'stderr_{}'.format(session_hash)
		}

	def _prepare_file_match_table(self):
		"""
		Each routine demands at least two files acting as an input/output.
		"""
		self.file_match_table = {
			'compress_input'		: None,
			'compress_output'		: self.aux_files['compress'],
			'decompress_input'		: self.aux_files['compress'],
			'decompress_output'		: self.aux_files['decompress'],
			'comparator_input'		: None,
			'comparator_output'		: self.aux_files['decompress']
		}

	def _prepare_libs(self):
		"""
		Registred routines are presented with own instances of Lib() class acting
		as a bridge between in-program representation of libraries' options and actual
		process invoking flags.
		"""
		self.libs = {
			'compress'		: Lib(),
			'decompress'	: Lib(),
			'comparator'	: Lib()
		}

		for lib in self.libs:
			if not self.libs[lib].prepare_lib():
				return False
		return True

	"""
	UTILS
	"""	
	def _store(self, col, payload):
		if self.config['log']:
			self.db.post(col, payload)

	def _check_dir_info(self):
		db = self.db.expose(defs.DB_DIR_SESSIONS)
		session_info = {}
		matched_dir = ''

		"""
		Before we actually refuse test without valid path already checked
		we try to match possible subpath
		"""
		#utils.msg_info('path', self.dir)
		for session in db.find({}, {'path': 1, "_id": 0}).distinct('path'):
			"""
			Path is present as-is, single match enough
			"""
			if session == self.dir:
				matched_dir = session
				break
			"""
			Path might be present in higher path, so we can
			use it as a springboard
			"""
			if self._is_dir_subpath(self.dir, session):
			 	matched_dir = session
			 	break
		"""
		We only accept dir information no older than 24h
		"""
		if matched_dir:
			session_info = db.find({'path': matched_dir}, {"_id": 0}).sort('timestamp', -1).limit(1)[0]
			if utils.create_timestamp() - session_info['timestamp'] > defs.DIR_CHECK_INTERVAL:
		 		utils.msg_error('dir', 'Information about \n"{}" \nare older than 24h. Please refresh directory.'.format(self.dir))
		 		return False
			return True
		else:
			utils.msg_error('recipe', 'No information about directory\n"{}"'.format(self.dir))
			return False
		

	def _is_dir_subpath(self, path, subpath):
		path_to_examine = path.split('/')
		for it, path_segment in enumerate(subpath.split('/')):
				if path_to_examine[it] != path_segment:
					return False
		return True


	def _get_dir_iterator(self):
		"""
		Use utilitarian dir fetch as a generator that is called individually
		to prevent single call exhaustion.
		"""
		limit = self.file_opts['limit']
		include = self.file_opts['include']
		exclude = self.file_opts['exclude']
		file_count = 0

		file_list = []
		for file in utils.get_path_recursive(self.dir, defs.PPM_REGEX):
			file_list.append(file)

		if limit:
			if limit < len(file_list):
				file_list = file_list[:limit]
			else:
				utils.msg_info('recipe', 'Used limit "{}" is higher than actual file count "{}"'.format(limit, len(file_list)))
		elif exclude:
			for file in file_list:
				for it in exclude:
					try:
						file.index(it)
						file_list.remove(file)
					except ValueError:
						continue
		elif include:
			filtered_file_list = []
			for file in file_list:
				for it in include:
					try:
						file.index(it)
						filtered_file_list.append(file)
					except ValueError:
						continue
			return filtered_file_list

		return file_list
