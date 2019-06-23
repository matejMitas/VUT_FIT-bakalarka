"""
@project: IBT19 - xmitas02
@brief: Fetching info about files
@author: Matej Mitas
@file: ibt19_dir_scanner.py
"""

"""
Generic library imports
"""
import subprocess
import pickle
import json
import datetime
import os
import re
import hashlib
from pprint import pprint
from termcolor import colored
"""
Functional imports
"""
import modules.ibt19_utils 		as utils
import modules.ibt19_defs 		as defs

class Dir_Scanner():
	def __init__(self, path, db, regex=None):
		self.path = path
		self.regex = regex
		self.db = db

	def scan(self):
		"""
		Scan directory
		"""
		self._prepare_dir_record()
		self.db.post(defs.DIR_SESS, self.dir)

		for item in utils.get_path_recursive(self.path, self.regex):
			self.db.post(defs.DIR_DATA, self._get_image_info(item))

	def _prepare_dir_record(self):
		timestamp = utils.create_timestamp()

		print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
		print(colored('> path \n\'{}\''.format(self.path), 'yellow'))
		print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

		self.dir = {
			'hash'		: utils.create_hash(self.path, timestamp),
			'path'		: self.path,
			'timestamp'	: timestamp
		}

	def _mdls_parse_format(self, line):
		return line.split('=')[-1].strip()

	def _mdls_parse_date(self, line):
		line = line.split(' ')
		retype = lambda x: int(x)

		date = list(map(retype, line[0].split('-')))
		time = list(map(retype, line[1].split(':')))
		time_zone = int(line[2])

		return datetime.datetime(date[0], date[1], date[2], time[0], time[1], time[2], time_zone)


	def _get_image_info(self, path):
		"""
		Read all fetched info about file
		"""
		ret = {}

		with open(defs.EXIF_ERR, "w+") as exif_err, \
	     	 open(defs.EXIF_PATH, "w+") as exif:
			return_code = subprocess.call(['exiftool', '-j', path], stdout=exif, stderr=exif_err)

		if (return_code == 0):
			with open(defs.EXIF_PATH, "r") as exif:
				"""
				EXIF data
				"""
				exif_data = json.loads(exif.read())[0]
				data = {
					'file'			: exif_data['FileName'],
					'path'			: exif_data['Directory'],
					'size'			: 0,
					'color_depth'	: exif_data['MaxVal'],
					'channels'		: 0,
					'date'			: {},
					'dims'			: {
						'width': exif_data['ImageWidth'],
						'height': exif_data['ImageHeight']
					}
				}

				statinfo = os.stat(path).st_size
				data['size'] = statinfo
				"""
				Determine image color depth by size comparision 
				"""
				possible_sizes 	= []
				dims 			= data['dims']['width'] * data['dims']['height']
				size_in_bits 	= data['size'] * 8
				for it in range(1,4):
					channels = it * 8
					possible_sizes.append(abs(size_in_bits - (dims * channels)))

				channels = possible_sizes.index(min(possible_sizes)) + 1
				if channels:
					data['channels'] = channels

				utils.msg_info('info read', data['file'])

			ret = {
				'hash'		: utils.create_hash('{}/{}'.format(data['path'], data['file']), None),
				'session'	: self.dir['hash'],
				'timestamp'	: utils.create_timestamp(),
				'ctx'		: data
			}
			
		os.remove(defs.EXIF_PATH)
		os.remove(defs.EXIF_ERR)
		return ret
