# Copyright (C) 2008 Jan Svec and Filip Jurcicek
# 
# YOU USE THIS TOOL ON YOUR OWN RISK!
# 
# email: info@gmail-backup.com
# 
# 
# Disclaimer of Warranty
# ----------------------
# 
# Unless required by applicable law or agreed to in writing, licensor provides
# this tool (and each contributor provides its contributions) on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied, including, without limitation, any warranties or conditions of
# TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR
# PURPOSE. You are solely responsible for determining the appropriateness of
# using this work and assume any risks associated with your exercise of
# permissions under this license. 

def Flag(arg):
	"""Flag conversion function
	"""
	argl = arg.lower()
	if argl in ['1', 'on', 'true']:
		return True
	elif argl in ['0', 'off', 'false']:
		return False
	else:
		raise ValueError("Not boolean argument: %r" % argl)

Bool = Flag

def Integer(arg):
	"""Integer conversion function

	:Parameters:
		- `arg`: string to convert
	
	:Returns: converted object
	:RType: int
	"""
	return int(arg)

def Float(arg):
	"""Float conversion function
	
	:Parameters:
		- `arg`: string to convert

	:Returns: converted object
	:RType: float
	"""
	return float(arg)

def String(arg):
	"""String conversion function (ie. no conversion)
	
	:Parameters:
		- `arg`: string to convert

	:Returns: converted object
	:RType: str
	"""
	return arg

def ListOf(arg, type, separator=','):
	"""List conversion function

	String ``arg`` is splited by ``separator``. On each resulting item is
	applied conversion function ``type``.

	:Parameters:
		- `arg`: string to convert
		- `type`: type of each item in list
		- `separator`: separator of items
	:Returns: converted objects
	:RType: list
	"""
	arg = arg.split(separator)
	return [type(i) for i in arg]

def DictOf(d, template, separators=':,'):
	"""Dictionary conversion function

	Converts string of key:value pairs into dictionary. Values of dictionary
	are converted using conversion functions in ``template``.

	:Parameters:
		- `template`: dictionary describing resulting dictionary
		- `separators`: 2-char string, 1st char specifies separator between
		  keys and values, 2nd char is separator between keys:values pairs
	:Returns: converted dictionary corresponding to ``template``
	:RType: dict
	"""
	sep_key, sep_item = separators
	d = [tuple(i.split(sep_key)) for i in d.split(sep_item)]
	d = dict(d)
	ret = {}
	for key, val in d.iteritems():
		try:
			conversion = template[key]
		except KeyError:
			raise ValueError, 'Unknown key %r' % key
		ret[key] = conversion(val)
	return ret

def FileInput(f, mode='', type=file):
	"""Input file conversion function

	This function opens file with name ``f`` for reading. Additional file modes
	can be specified using ``mode`` parameter.

	:Parameters:
		- `f`: File name (option value)
		- `mode`: Additional file mode (eg. ``'b'`` for binary access). ``'r'``
		  is automatically added to this mode.
		- `type`: Type of opened file. You can for example use another file
		  type as StringIO.
	
	:Returns: Created file object
	:RType: file
	"""
	mode = 'r' + mode
	return type(f, mode)

def FileOutput(f, mode='', type=file):
	"""Output file conversion function

	This function opens file with name ``f`` for writing. Additional file modes
	can be specified using ``mode`` parameter. It is useful for writing return
	values of main function.

	:Parameters:
		- `f`: File name (option value)
		- `mode`: Additional file mode (eg. ``'b'`` for binary access). ``'w'``
		  is automatically added to this mode.
		- `type`: Type of opened file. You can for example use another file
		  type as StringIO.
	
	:Returns: Created file object
	:RType: file
	"""
	mode = 'w' + mode
	return type(f, mode)

def ScriptInput(f, mode='', type=file):
	if f == '-':
		return sys.stdin
	else:
		return FileInput(f, mode, type)

def ScriptOutput(f, mode='', type=file):
	if f == '-':
		return sys.stdout
	else:
		return FileOutput(f, mode, type)

