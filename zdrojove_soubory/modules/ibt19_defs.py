"""
@project: IBT19 - xmitas02
@brief: Variables, constants, flags...
@author: Matej Mitas
@file: ibt19_defs.py
"""

"""
Generic library imports
"""
import subprocess


TEMP_PATH 			= './temp'
TEMP_SAVED_PATH 	= './temp_saved'
OUT_PATH 			= './out'
JSON_PATH 			= './json'
GRAPH_PATH 			= '../bc_thesis/obrazky-figures'
# 
STD_ERR_FILE 		= './temp/err'
STD_OUT_FILE 		= './temp/out'
#
PPM_REGEX 			= r'\.ppm|\.pgm';
TIF_REGEX 			= r'\.tif';

"""
PSNR
"""
MAX_BITS 			= 255
CRITERION_LOSSLESS	= 100
ERR_IMG				= 0
PSNR_PRECISION 		= 0.02
PSNR_LOOP_PREVENTION_VALUES = 5
# knihovny
LIBS 				= {
	'kakadu_compress'		: 'kdu_compress',
	'openjpg_compress'		: 'opj_compress',
	'kakadu_decompress'		: 'kdu_expand',
	'openjpg_decompress'	: 'opj_decompress',
	'comparator'			: 'pnmpsnr'
}
MEASURE_TIME 		= ['/usr/bin/time']
# 
PNMPSNR 			= 'pnmpsnr'
EXIF 				= 'exiftool'
EXTRA_INFO			= 'mdls'
# 
ARGS_INPUT 			= 1
ARGS_OUTPUT 		= 3

MDLS_PATH 			= './temp/mdls'
EXIF_PATH 			= './temp/exif'
EXIF_ERR 			= './temp/exif_err'

DIR_SESS 			= 'dir_sessions'
DIR_DATA 			= 'dir_data'
TEST_SESS 			= 'test_session'
TEST_DATA 			= 'test_data'

COMPRESS 			= 'compress'
DECOMPRESS 			= 'decompress'
COMPARATOR			= 'comparator'

DB_DIR_SESSIONS 	= 'dir_sessions'
DB_DIR_DATA 		= 'dir_data'
DB_TEST_SESSIONS	= 'test_sessions'
DB_TEST_DATA		= 'test_data'

DIR_CHECK_INTERVAL 	= 86400

TEST_APRX 			= 'approximation'
TEST_FINAL 			= 'final'

REPETITON_COUNT 	= 10

FETCHED_VALUES		= 'fetched_values'
FETCHED_COMRPRESS	= 'fetched_compress'
FETCHED_DECOMPRESS  = 'fetched_decompress'