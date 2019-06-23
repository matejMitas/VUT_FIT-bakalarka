"""
@project: IBT19 - xmitas02
@brief: Utils
@author: Matej Mitas
@file: ibt19_utils.py
"""

"""
Generic library imports
"""
import json
import subprocess
import time
import os
import numpy
import math
import cv2
import re
from termcolor import colored
import time
import datetime
import hashlib
import pickle
"""
Functional imports
"""
import modules.ibt19_defs		as defs


def clear_aux_files():
	"""
	Files used as a container need to get discarted. 
	"""
	try:
		for file in get_path_recursive(defs.TEMP_PATH, None):
			os.remove(file)
	except IOError:
		utils.msg_info('IO', 'Couldn\'t remove all files, please take care of "./temp"')

"""
Timestamps and hashes
"""
def create_timestamp():
	return time.time()

def readable_timestamp(timestamp):
	return datetime.datetime.fromtimestamp(timestamp)

def convert_time_timestamp(*args):
	return float(datetime.datetime(*args).strftime('%s'))

def create_hash(name, timestamp=None):
	return hashlib.md5(pickle.dumps({
		'name': name,
		'timestamp': timestamp if timestamp else create_timestamp()
	})).hexdigest()

"""
Colored print for program output
"""
def msg_error(origin, string, **kwargs):
	print(colored('✗ ({}) - {}'.format(origin, string), 'red'))

def msg_info(origin, string, **kwargs):
	print(colored('↠ ({}) - {}'.format(origin, string), 'cyan'))

def msg_test(origin, string, **kwargs):
	is_without_newline = '\n'
	for key in kwargs:
		if key == 'no_newline':
			is_without_newline = ''

	if origin:
		print(colored('✓ ({}) - {}'.format(origin, string), 'magenta'), end=is_without_newline)
	else:
		print(colored(' {}'.format(string), 'magenta'), end=is_without_newline)


def msg_done(origin, string, **kwargs):
	is_without_newline = '\n'
	for key in kwargs:
		if key == 'no_newline':
			is_without_newline = ''

	if origin:
		print(colored('✓ ({}) - {}'.format(origin, string), 'green'), end=is_without_newline)
	else:
		print(colored(' {}'.format(string), 'green'), end=is_without_newline)

def msg_compare(value, is_final):
	print(' {}'.format(colored(
		'{}dB'.format(value),
		'white' if is_final else 'white',
		'on_green' if is_final else 'on_magenta',
		attrs=['bold']
	)))

"""
Markers for session
"""
def msg_session_start(name, hash):
	print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
	print(colored('> Starting \'{}\''.format(name), 'yellow'))
	print(colored('> Hash \'{}\''.format(hash), 'yellow'))
	print(colored('> {}'.format(datetime.datetime.now()), 'yellow'))
	print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')

def msg_session_end(name, hash):
	print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
	print(colored('> Ending \'{}\''.format(name), 'yellow'))
	print(colored('> Hash \'{}\''.format(hash), 'yellow'))
	print(colored('> {}'.format(datetime.datetime.now()), 'yellow'))
	print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')
	print('--------------------------------------------------------------')

"""
Welcome message
"""
def msg_welcome():
	print('\n\
________________  __     ______     _______  _________________     	\n\
//////////////// / /\   /\  ==  \  /\_____/ //////////////////     	\n\
                 \ \ \  \ \  __<   \/_/\ \      					\n\
    xmitas02      \ \_\  \ \_____\    \ \_\     2018 - 2019     	\n\
                   \/_/   \/_____/     \/_/   						\n\
==============================================================		\n\
-------------------------------------------------------------- 		\
	')

def separator():
	print('--------------------------------------------------------------')


def construct_path(file_name):
	"""
	For accesing temp easily
	"""
	return './temp/{}'.format(file_name)


def invoke_process(args, stdout_path, stderr_path, measure_ram):
	"""
	Process time and memory handling
	"""
	if (measure_ram):
		args = defs.MEASURE_TIME + args

	with open(construct_path(stdout_path), "w+") as err, \
		 open(construct_path(stderr_path), "w+") as out:
	
		start = time.time()
		ret = subprocess.call(args, stdout=out, stderr=err)
		end = time.time()

		if (ret != 0):
			msg_error('failed', 'Executed "{}", yet failed with exit code: {}'.format(args[2], ret))
			return -1

		return round(end - start, 8)

def check_folder_presence(folder_name):
	if not os.path.exists(folder_name):
   		os.makedirs(folder_name)


def check_libraries():
	"""
	All libraries present for testing. First, all folders 
	need to exist, then libraries 
	"""
	check_folder_presence(defs.TEMP_PATH)
	check_folder_presence(defs.TEMP_SAVED_PATH)
	check_folder_presence('./graphs')


	try:
		subprocess.check_output(['kdu_compress', '-v'])
		msg_done('kdu_compress', 'Kakadu compress present')
	except OSError:
		msg_error('kdu_compress', 'Kakadu compress not available')
		return False

	try:
		subprocess.check_output(['exiftool'])
		msg_done('exiftool', 'Exiftool present')
	except OSError:
		msg_error('exiftool', 'Exiftool not available')
		return False
	
	try:
		subprocess.check_output(['kdu_expand', '-v'])
		msg_done('kdu_deompress', 'Kakadu decompress present')
	except OSError:
		msg_error('kdu_decompress', 'Kakadu decompress not available')
		return False

	try:
		subprocess.check_output(['opj_compress', '-h'])
	except OSError:
		print(colored('✖ (opj_compress)    OpenJPG compress not available', 'red'))
		return False
	except subprocess.CalledProcessError:
		msg_done('opj_compress', 'OpenJPG compress present')

	try:
		subprocess.check_output(['opj_decompress', '-h'])
	except OSError:
		print(colored('✖ (opj_decompress)    OpenJPG decompress not available', 'red'))
		return False
	except subprocess.CalledProcessError:
		msg_done('opj_decompress', 'OpenJPG decompress present')

	try:
		subprocess.check_output(['pnmpsnr'], stderr=subprocess.STDOUT)
	except OSError:
		print(colored('✖ (pnmpsnr)         PSNR comparator not available', 'red'))
		return False
	except subprocess.CalledProcessError:
		msg_done('pnmpsnr', 'PSNR comparator present')

	separator()
	return True

def get_path_file(string):
	divider = string.rfind('/')
	return {
		'path': string[:divider],
		'file': string[divider+1:]
	}

def get_memory_usage(stdout_path):
	"""
	Read used memory from '/usr/bin/time' output
	"""
	full_path = construct_path(stdout_path)
	if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
		with open(full_path, "r") as err:
			return int(err.read().strip().split('\n')[1].strip().split(' ')[0]) / 1000000

def get_psnr(stdout_path):	
	"""
	Read PSNR from 'pnmpsnr' output
	"""
	with open(construct_path(stdout_path), "r") as data:
		vals = data.read().strip().split('\n')

		val1 = float(vals[1].strip().split(' ')[-2])
		if (val1 == 'no'):
			return 100
		"""
		For RGB8 and Gray8 images
		"""
		try:
			val2 = float(vals[2].strip().split(' ')[-2])
			val3 = float(vals[3].strip().split(' ')[-2])

			val = round((val1+val2+val3) / 3, 4)
			return float(val)
		except ValueError:
			return float(val1)

def get_path_recursive(path, regex=None):
	if not regex:
		regex =  r'.'

	for entry in os.scandir(path):
		if entry.is_dir():
			yield from get_path_recursive(entry.path, regex)
		elif not entry.name.startswith('.') and entry.is_file():
			regex = re.compile(regex)
			regex_ret = re.search(regex, entry.name)
			if (regex_ret):
				yield entry.path
				