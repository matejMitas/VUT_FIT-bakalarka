"""
@project: IBT19 - xmitas02
@brief: Graphs
@author: Matej Mitas
@file: ibt19_graph_draw.py
"""

"""
Generic library imports
"""
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as plticker
import matplotlib.image as mpimg
from matplotlib.ticker import ScalarFormatter
import cv2
import numpy
import pickle
import hashlib
import math
import ast
from pprint import pprint
"""
Functional imports
"""
import modules.ibt19_defs as defs
import modules.ibt19_utils as utils


class Graph_Draw:
	def __init__(self, config, db):
		self.config = config

		self.db_data = db.expose(defs.DB_TEST_DATA)
		self.db_dir_data = db.expose(defs.DB_DIR_DATA)
		self.db_sessions = db.expose(defs.DB_TEST_SESSIONS)

		self.graph_names = []

		self.all_files = []

	def execute(self):
		"""
		Firstly, we need to decide upon which graph type
		are we trying to render
		"""
		graph_blueprint = self.config['blueprint']
		"""
		Every single graph - except 'aprx_quality' requires
		fetching and processing data
		"""
		if graph_blueprint != 'aprx_quality':
			"""
			Set up data for drawing
			"""
			self.sessions = self.config['sessions']
			self._fetch_data()

			"""
			Invoke method handling data drawing
			"""
			try:
				graph_blueprint.index('test_')
				self._graph_blueprint_test()
			except ValueError:


				self._graph_blueprint_aprx()

		else:
			self._graph_blueprint_aprx_quality()

		print('')


	def _graph_blueprint_aprx(self):
		markers = ['s', 'o', '^', 'p', 'X', 'X']
		axis_data = self._graph_layout(blueprint='aprx')
		"""
		Two graphs side by side
		"""

		for index_it, graph_index in enumerate(self.fetched_data):
			"""
			Match data for single graph
			"""
			graph_data 	= self.fetched_data[graph_index]
			"""
			Aux data
			"""
			leg 		= []
			colors 		= self._match_colors(self.graph_names[index_it])
			settings 	= self._graph_get_settings(index_it)

			utils.msg_info('graph', self.graph_names[index_it])
			#print(settings)

			"""
			Get graph data
			"""
			for data_it, graph_key in enumerate(graph_data):
				data_source = graph_data[graph_key]

				main_axis_labels = list(data_source.keys())
				main_axis_indexes = numpy.arange(0, len(main_axis_labels))

				"""
				Sort main labels
				"""
				main_axis_labels = self._process_main_axis(main_axis_labels)
				auxiliary_data = []	

				for variant in main_axis_labels:
					auxiliary_data.append(numpy.average(data_source[variant]['value']))

				main_axis_labels = self._prettify_main_axis(main_axis_labels)

				selected_color = colors[-1] if graph_key == 'True' else colors[data_it]
				axis_data[index_it].plot(main_axis_labels, auxiliary_data, marker=markers[data_it], linewidth=1, color=selected_color)
				leg.append('{} bpp'.format(graph_key))

			"""
			Set labels and titles
			"""
			axis_data[index_it].set_title(settings['title'])
			axis_data[index_it].set_xlabel(settings['x'])
			axis_data[index_it].set_ylabel(settings['y'])
			axis_data[index_it].grid(alpha=0.5, which="major", ls="-", axis='y')
			"""
			Aux settings
			"""
			axis_data[index_it].set_ylim(settings['limits'][0], settings['limits'][1])

			if len(leg) > 1:
				axis_data[index_it].legend(leg)


		axis_data[0].tick_params(axis='x', rotation=-45)
		plt.subplots_adjust(left=0.05, right=0.97, top=0.90, bottom=0.175)

		self._graph_save(plt)

	def _graph_blueprint_test(self):
		"""
		Prepare individual types
		"""
		d = ['výkon', 'komprese', 'dekomprese']
		s = ['exam', 'compress', 'decompress']

		markers = ['s', 'o', '^', 'p', 'X', '+', 'x', 'D']
		axis_data = self._graph_layout(blueprint=self.config['blueprint'])
		"""
		Get graph data
		"""
		for index_it, graph_index in enumerate(self.fetched_data):
			graph_data = self.fetched_data[graph_index]

			leg 		= []

			try:
				self.config['sessions'][index_it]['mixed_sessions']
				colors 	= self._match_colors('mix_')
			except KeyError:
				colors 	= self._match_colors(self.graph_names[index_it])
				

			
			settings 	= self._graph_get_settings(index_it)


			utils.msg_info('graph', self.graph_names[index_it])

			"""
			Calculate bar offset
			"""
			bar_opts = len(list(graph_data.keys()))
			if bar_opts > 1:
				bar_offset = bar_opts / 4

			for data_it, graph_key in enumerate(graph_data):
				source = graph_data[graph_key]

				main_axis_labels = list(source.keys())
				main_axis_indexes = numpy.arange(0, len(main_axis_labels))

				main_axis_labels = self._process_main_axis(main_axis_labels)
				
				auxiliary_data = {
					'value'			: [],
					'compress'		: [],
					'decompress'	: []
				}

				for variant in main_axis_labels:
					auxiliary_data['value'].append(numpy.average(source[variant]['value']))
					"""
					Normalize time for ns
					"""
					auxiliary_data['compress'].append(numpy.average(source[variant]['time_compress'])*10**9)
					auxiliary_data['decompress'].append(numpy.average(source[variant]['time_decompress'])*10**9)

				
				#print(auxiliary_data)

				for i in range(0,3):
					key = list(auxiliary_data.keys())[i]
					prepared_data = auxiliary_data[key]
					"""
					Normalizace for double data source graph
					"""
					saved_i = i
					if i == 2:
						i = 1

					graph_type = settings[i]['type']

					try:
						highlighted_opt = settings[data_it]['highlighted_opt']
						point = auxiliary_data[key][highlighted_opt]
						axis_data[i].axhline(y=point, color='r', linestyle='-', linewidth=1)
					except KeyError:
						pass
					except IndexError:
						pass

					if graph_type == 'plot':
						print(prepared_data)
						axis_data[i].plot(main_axis_indexes, prepared_data)

					elif graph_type == 'bar':
						if i:
							x = main_axis_indexes + ((saved_i-1.5) * 0.15)
						else:
							x = main_axis_indexes 
						bars = axis_data[i].bar(x, prepared_data, width=0.15)

		"""
		Set metadata for graphs
		"""
		for i in range(0,2):

			sett = settings[i]
			if 'legend' in sett:
				axis_data[i].legend(sett['legend'])

			if i > 0:
				axis_data[i].set_ylim(sett['limits'][0], sett['limits'][1])
			else:
				if 'scale' in sett:
					if sett['scale'] == 'log':
						axis_data[i].set_yscale('log')
						axis_data[i].set_ylim(0.05, 15)
				else:
					axis_data[i].set_ylim(sett['limits'][0], sett['limits'][1])
			
			axis_data[i].set_axisbelow(True)
			axis_data[i].grid(alpha=1, which="major", ls="-", axis='y')
			axis_data[i].grid(alpha=0.25, which="minor", ls="dotted")

			axis_data[i].set_title(sett['title'])
			axis_data[i].set_xlabel(sett['x'])
			axis_data[i].set_ylabel(sett['y'])

			axis_data[i].set_xticks(main_axis_indexes)

			if 'labels' in sett:
				axis_data[i].set_xticklabels(sett['labels'])
			else:
				axis_data[i].set_xticklabels(main_axis_labels)

			if 'rotation' in sett:
				axis_data[i].tick_params(axis='x', rotation=-45)

		if self.config['blueprint'] == 'test_small':
			plt.subplots_adjust(left=0.075, right=0.97, top=0.90, bottom=0.15)
		else:
			plt.subplots_adjust(left=0.1, right=0.97, top=0.95, bottom=0.075)

		self._graph_save(plt)


	def _graph_layout(self, **kwargs):
		"""
		Create desired layout and spacing
		"""
		keys = list(kwargs.keys())
		if len(keys) == 1 and keys[0] == 'blueprint':
			blueprint_type = kwargs['blueprint']
			axis_data = []

			if blueprint_type == 'aprx':
				figsize = (12,4)
				opt = {
						'nrows'		: 1,
						'ncols'		: 5,
						'wspace'	: 0.3
				}

			elif blueprint_type == 'test_small':
				figsize = (8,3.5)
				opt = {
						'nrows'		: 1,
						'ncols'		: 2,
						'wspace'	: 0.2
				}

			elif blueprint_type == 'test_big':
				figsize = (8,8)
				opt = {
						'nrows'		: 2,
						'ncols'		: 1,
						'hspace'	:	0.35
				}

			
			figure = plt.figure(figsize=figsize)
			gs = gridspec.GridSpec(**opt)
			axis_data = []


			if blueprint_type == 'aprx':
				axis_data.append(figure.add_subplot(gs[0, 0:3]))
				axis_data.append(figure.add_subplot(gs[0, 3:]))

			elif blueprint_type == 'test_small':
				axis_data.append(figure.add_subplot(gs[0, 0:1]))
				axis_data.append(figure.add_subplot(gs[0, 1:2]))

			elif blueprint_type == 'test_big':
				axis_data.append(figure.add_subplot(gs[0, 0:]))
				axis_data.append(figure.add_subplot(gs[1, 0:]))

		return axis_data

	def _graph_blueprint_aprx_quality(self):
		"""
		Draw quality image graph
		"""
		used_files = self.config['used_files']
		axis_data = []

		print(used_files)

		fig = plt.figure(figsize=(8,4))
		gs = gridspec.GridSpec(nrows=1, ncols=3, hspace=0.2, wspace=0.02)

		files = []
		utils.msg_info('graph', 'quality_graph')
		"""
		Fix for lossless quality
		"""
		for file in utils.get_path_recursive(self.config['source']):
			last_file = file
			"""
			Opt matching according to file name
			"""
			cur_opt = file[file.rfind('+')+1:file.rfind('.')]
			if cur_opt in used_files:
				files.append(file)

		for i in range(0, len(files)):
			"""
			Create graph
			"""
			axis_data.append(fig.add_subplot(gs[0, i:i+1]))
			"""
			Remove ticks
			"""
			axis_data[i].set_xticks([])
			axis_data[i].set_yticks([])
			"""
			Prepare and show image
			"""
			img = cv2.imread(files[i])
			axis_data[i].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
			"""
			Set label
			"""
			if used_files[i] == 'lossless':
				label = 'bezeztrátové'
			else:
				label = '{} bpp\n'.format(used_files[i])
			axis_data[i].set_xlabel(label, labelpad=10)

		plt.subplots_adjust(left=0.05, right=0.97, top=0.90, bottom=0.1)
		self._graph_save(plt)


	def _graph_get_settings(self, index):
		return self.config['sessions'][index]['graph_settings']

	def _graph_save(self, plt):
		name = self.config['output']['name']
		folder = '{}/{}'.format(defs.GRAPH_PATH, self.config['output']['folder'])
		"""
		If needed create folder in main graph directory
		"""
		utils.check_folder_presence(folder)
		"""
		Save both vector and raster version
		"""
		#plt.savefig('{}/{}.eps'.format(folder, name))
		plt.savefig('./graphs/{}.png'.format(name))


	def _match_colors(self, name): 
		colors = {
			'fotky'				: ['#8db8f4', '#4b5cdb', '#1c0c95', '#0b0252'],
			'mapy'				: ['#86eef7', '#39d3e0', '#139fab', '#085c64'],
			'scany'				: ['#e5ed5f', '#c5cd3d', '#a7af1e', '#7f8609'],
			'bitonal-single'	: ['#ff9797', '#e44f4f', '#b51f1f', '#810b0b'],
			'bitonal'			: ['#fac985', '#de942c', '#925a0b', '#523102'],
			'mix'				: ['#bababa', '#7e7e7e', '#454545', '#191919'],
		}

		try:
			return colors[name.split('_')[0]]
		except IndexError:
			return colors[0]

	def _process_main_axis(self, axis_data):
		"""
		Due to the nature of store data we might encouter
		alfanumeric and string values
		"""

		try:
			axis_data.sort(key = float)
		except ValueError:
			axis_data.sort()

		return axis_data

	def _prettify_main_axis(self, axis_data):
		for it, item in enumerate(axis_data):
			"""
			If it's needed to trim superfluous zeros
			"""
			try:
				possible_decimal_after_dot = float(item.split('.')[1])
				if not possible_decimal_after_dot:
					axis_data[it] = item.split('.')[0]
			except IndexError:
				pass


		return axis_data

	def _add_to_fetched(self, stream, **kwargs):

		allowed_options = ['init_stream', 'init_saving', 'saving_value', 'value', 'time_compress', 'time_decompress']
		selected_options = []

		for key, value in kwargs.items():
			if key not in allowed_options:
				utils.msg_error('fetching', 'unknown option adding to fetched values')
				return
			else:
				selected_options.append(key)
		"""
		When we want to add empty dictionary it's logical we're just 
		doing ground work so if it's already in place there's no need
		to add it as is
		"""
		if len(selected_options) == 1:
			sel =  selected_options[0]
			if sel == allowed_options[0]:
				if stream not in self.fetched_data[self.curr_name].keys():
					self.fetched_data[self.curr_name][stream] = {}

			elif sel == allowed_options[1]:
				if value not in self.fetched_data[self.curr_name][stream].keys():
					self.fetched_data[self.curr_name][stream][value] = {
						'value'				: [],
						'time_compress'	 	: [],
						'time_decompress'	: []
					}
		
		else:
			"""
			Adding values
			"""
			if 'value' in kwargs:
				self.fetched_data[self.curr_name][stream][kwargs['saving_value']]['value'].append(kwargs['value'])
			if 'time_compress' in kwargs:
				self.fetched_data[self.curr_name][stream][kwargs['saving_value']]['time_compress'].append(kwargs['time_compress'])
			if 'time_decompress' in kwargs:
				self.fetched_data[self.curr_name][stream][kwargs['saving_value']]['time_decompress'].append(kwargs['time_decompress'])
			


	
	def _fetch_data(self):
		"""
		Prepare data wrappers
		"""
		self.fetched_data = {}
		#self.fetched_compress_time = {}
		#self.fetched_decompress_time = {}

		for session_blueprint in self.sessions:
			session_name 		= session_blueprint['name']

			self.graph_names.append(session_name)
			self._fetch_session_data(session_blueprint, session_name)


	def _fetch_session_data(self, session_blueprint, session_name):
		"""
		Loop through all sessions entered in recipe as a source 
		"""
		#print('')
		#utils.msg_info('session', session_name)
		"""
		Create a place to store data belonging to particular graph
		"""
		self.fetched_data[session_name] = {}
		self.curr_name = session_name
		"""
		Get all its testing sessions
		"""
		for session_hash in session_blueprint['input']:
			self._fetch_session_input(session_hash, session_blueprint)


	def _fetch_session_input(self, session_hash, graph_session_blueprint):
		session_query = {'hash': session_hash}
		"""
		Track all files used in session for statistical purposes
		"""
		for input_file in self.db_data.find(session_query).distinct('ctx.file.name'):
			if input_file not in self.all_files:
				self.all_files.append(input_file)
		"""
		Fetch session data
		"""
		try:
			data_session_settings = self.db_sessions.find_one(session_query)['ctx']
		except TypeError:
			utils.msg_error('session', 'Session {} does not exist'.format(session_name))
			return False

		variants 	= data_session_settings['file_types']
		"""
		Get main axis ordering
		"""
		streams, values = self._fetch_session_axis(session_hash, graph_session_blueprint, data_session_settings)

		for stream in streams:
		 	#print(graph_session_blueprint['data_settings']['values'])
		 	self._fetch_session_stream(session_hash, stream, values, graph_session_blueprint['data_settings']['values'])


	def _fetch_session_stream(self, hash, stream, values, value_type):
		#print()
		#utils.msg_test('stream', stream)
		"""
		Prepared streams in the main structure
		"""
		stream = str(stream)
		self._add_to_fetched(stream, init_stream=True)

		for value in values:
			"""
			A little bit of ambigiousity is need to facilitate matching
			in dabatase (needs specific var types) and saving (only string)
			"""
			saving_value 	= str(value)
			matching_value 	= None
			"""
			Retype for database matching
			"""
			try:
				if type(value) != bool:
					matching_value = float(value)
				else:
					matching_value = bool(value)
			except ValueError:
				if matching_value == 'True':
					matching_value = True
				elif matching_value == 'False':
					matching_value = False
			except TypeError:
				pass
				matching_value = ast.literal_eval(saving_value)

			"""
			First occurence of particular flag yields need for data
			setting
			"""
			self._add_to_fetched(stream, init_saving=saving_value)
			#utils.msg_done('index', saving_value)

			"""
			Data fetching
			"""
			if value_type == 'opts':
				for item in self.db_data.find({'session': hash, 'ctx.testing_opt': matching_value, 'ctx.quality': float(stream)}):

					item = item['ctx']
					self._fetch_final_record(stream, saving_value, item['rate']['calculated'], item)

			elif value_type == 'criterion':
				if stream == 'True':
					temp_stream = True
				elif stream == 'False':
					temp_stream = False
				else:
					temp_stream = stream
				
				try:
					temp_stream.index('[')
					temp_stream = ast.literal_eval(temp_stream)
				except ValueError:
					pass
				except AttributeError:
					pass

				for item in self.db_data.find({'session': hash, 'ctx.rate.used': matching_value, 'ctx.testing_opt': temp_stream}):
					item = item['ctx']
					self._fetch_final_record(stream, saving_value, item['quality'], item)

			elif value_type == 'megapixels':
				regex = '{}\.'.format(int(value))
				for item in self.db_data.find({'session': hash, 'ctx.rate.used': float(stream), 'ctx.file.name': {'$regex': regex}}):
					item = item['ctx']
					self._fetch_final_record(stream, saving_value, item['quality'], item)
					

	def _fetch_final_record(self, stream, saving_value, given_value, item):

		x,y = self._fetch_image_dims(item['file'])

		compress_time = item['compression']['time'] / (x*y)
		decompress_time = item['decompression']['time'] / (x*y)

		self._add_to_fetched(
			stream, 
			saving_value=saving_value, 
			value=given_value, 
			time_compress=compress_time,
			time_decompress=decompress_time
		)

	def _fetch_session_axis(self, hash, graph_session_blueprint, data_session_settings):
		"""
		Create iterables for structural handling of graphs
		"""
		possible_opts 	= {
			'criterion' : data_session_settings['compress']['criterion']['value'],
			'opts'		: data_session_settings['opts']
		}
		values = []
		"""
		Streams are pretty straight forward, just matching, only two possible options
		"""
		streams 		= possible_opts[graph_session_blueprint['data_settings']['streams']]
		"""
		Values might require more advanced matching
		"""
		try:
			values 			= possible_opts[graph_session_blueprint['data_settings']['values']]
		except KeyError: 
			value_type = graph_session_blueprint['data_settings']['values']

			if value_type == 'megapixels':
				options = self.db_data.find({'session': hash}).distinct('ctx.file.name')
				for opt in options:
					try:
						megapixels = float(opt.split('.')[0].split('+')[1])
						if megapixels not in values:
							values.append(megapixels)
					except IndexError:
						"""
						File that are not recognized as a resolution testing files are
						not skipped and therefore not utilised
						"""
						pass

		return [streams, values]

	def _fetch_image_dims(self, image_info):
		try:
			data = self.db_dir_data.find({'ctx.file': image_info['name'], 'ctx.path': image_info['path']}).sort('timestamp', -1).limit(1)[0]
			return [data['ctx']['dims']['width'], data['ctx']['dims']['height']]
		except IndexError:
			return False


	def _process_db_data(self, cursor, graph_type):
		payload = []
		for item in cursor:
			if graph_type == 'criterion':
				payload.append(item['ctx']['quality'])
			elif graph_type == 'opts':
				payload.append(item['ctx']['rate']['calculated'])

		return payload

	def _check_sessions_compatibilty(self):
		hashed_settings = []
		for session in self.session_data:
			session_settings = self.db_sessions.find({'hash': session})[0]['ctx']
			hashed = None

			if self.session_mode == 'strict':
				hashed = hashlib.md5(pickle.dumps(session_settings)).hexdigest()

			elif self.session_mode == 'normal':
				filtered_session_settings = {}
				for key in session_settings.keys():
					if key.find('params') != -1:
						filtered_session_settings[key] = session_settings[key]
				hashed = hashlib.md5(pickle.dumps(filtered_session_settings)).hexdigest()
			
			hashed_settings.append(hashed)

		if len(set(hashed_settings)) != 1:
			utils.msg_error('recipe', 'Can\'t create graphs from mutually not compatabile sessions')
			return False

		return True
