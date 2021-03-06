"""
A customized logger for pyppl
"""
import logging
import re
import sys
from copy import copy as pycopy
from colorama import init as coloramaInit, Fore, Back, Style
# Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL 
from .utils import Box
from .exception import LoggerThemeError
from .template import TemplateLiquid

coloramaInit(autoreset = False)

# the entire format
LOGFMT = "[%(asctime)s%(message)s"

# the themes
# keys:
# - no colon: match directory
# - in: from the the list
# - starts: startswith the string
# - re: The regular expression to match
# - has: with the string in flag
THEMES = {
	'greenOnBlack': Box([
		('DONE',     Style.BRIGHT + Fore.GREEN),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
					 # levelname color,         message color
		('PROCESS',  [Style.BRIGHT + Fore.CYAN, Style.BRIGHT + Fore.CYAN]),
		('DEPENDS',  Fore.MAGENTA),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.GREEN),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.WHITE)
	]),
	'blueOnBlack':  Box([
		('DONE',     Style.BRIGHT + Fore.BLUE),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
		('PROCESS',  [Style.BRIGHT + Fore.CYAN, Style.BRIGHT  + Fore.CYAN]),
		('DEPENDS',  Fore.GREEN),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.BLUE),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.WHITE)
	]),
	'magentaOnBlack':  Box([
		('DONE',     Style.BRIGHT + Fore.MAGENTA),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
		('PROCESS',  [Style.BRIGHT + Fore.GREEN, Style.BRIGHT + Fore.GREEN]),
		('DEPENDS',  Fore.BLUE),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.MAGENTA),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.WHITE)
	]),
	'greenOnWhite': Box([
		('DONE',     Style.BRIGHT + Fore.GREEN),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
		('PROCESS',  [Style.BRIGHT + Fore.BLUE, Style.BRIGHT + Fore.BLUE]),
		('DEPENDS',  Fore.MAGENTA),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.GREEN),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.BLACK)
	]),
	'blueOnWhite':  Box([
		('DONE',     Style.BRIGHT + Fore.BLUE),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
		('PROCESS',  [Style.BRIGHT + Fore.GREEN, Style.BRIGHT + Fore.GREEN]),
		('DEPENDS',  Fore.MAGENTA),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.BLUE),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.BLACK)
	]),
	'magentaOnWhite':  Box([
		('DONE',     Style.BRIGHT + Fore.MAGENTA),
		('DEBUG',    Style.BRIGHT + Fore.BLACK),
		('PROCESS',  [Style.BRIGHT + Fore.BLUE, Style.BRIGHT + Fore.BLUE]),
		('DEPENDS',  Fore.GREEN),
		('in:INFO,P.PROPS,OUTPUT,EXPORT,INPUT,P.ARGS,BLDING,SUBMIT,RUNNING,JOBDONE,KILLING', Fore.MAGENTA),
		('CMDERR',   Style.BRIGHT + Fore.YELLOW),
		('has:ERR',  Fore.RED),
		('in:WARNING,RETRY,RESUMED,SKIPPED',  Style.BRIGHT + Fore.YELLOW),
		('in:WORKDIR,CACHED,P.DONE', Fore.YELLOW),
		('',         Fore.BLACK)
	])
}

LEVELS = {
	'all':     ['INPUT', 'OUTPUT', 'P.ARGS', 'P.PROPS', 'DEBUG'],
	'basic':   [],
	'normal':  ['INPUT', 'OUTPUT', 'P.ARGS', 'P.PROPS']
}

LEVELS_ALWAYS = [
    'PROCESS', 'WORKDIR', 'RESUMED', 'SKIPPED', 'DEPENDS', 'STDOUT', 'STDERR', 'WARNING', 
    'ERROR', 'INFO', 'DONE', 'EXPORT', 'PYPPL', 'TIPS', 'CONFIG', 'CMDOUT', 'CMDERR', 'BLDING', 
    'SUBMIT', 'RUNNING', 'RETRY', 'JOBDONE', 'KILLING', 'P.DONE', 'CACHED'
]

DEBUG_LINES = {
	'EXPORT_CACHE_OUTFILE_EXISTS'  : -1,
	'EXPORT_CACHE_USING_SYMLINK'   : 1,
	'EXPORT_CACHE_USING_EXPARTIAL' : 1,
	'EXPORT_CACHE_EXFILE_NOTEXISTS': 1,
	'EXPORT_CACHE_EXDIR_NOTSET'    : 1,
	'CACHE_EMPTY_PREVSIG'          : -1,
	'CACHE_EMPTY_CURRSIG'          : -2,
	'CACHE_SCRIPT_NEWER'           : -1,
	'CACHE_SIGINVAR_DIFF'          : -1,
	'CACHE_SIGINFILE_DIFF'         : -1,
	'CACHE_SIGINFILE_NEWER'        : -1,
	'CACHE_SIGINFILES_DIFF'        : -1,
	'CACHE_SIGINFILES_NEWER'       : -1,
	'CACHE_SIGOUTVAR_DIFF'         : -1,
	'CACHE_SIGOUTFILE_DIFF'        : -1,
	'CACHE_SIGOUTDIR_DIFF'         : -1,
	'CACHE_SIGFILE_NOTEXISTS'      : -1,
	'EXPECT_CHECKING'              : -1,
	'INFILE_RENAMING'              : -1,
	'INFILE_EMPTY'                 : -1,
	'SUBMISSION_FAIL'              : -3,
	'OUTFILE_NOT_EXISTS'           : -1,
	'OUTDIR_CREATED_AFTER_RESET'   : -1,
	'SCRIPT_EXISTS'                : -2,
	'JOB_RESETTING'                : -1
}

def _getColorFromTheme (level, theme):
	"""
	Get colors from a them
	@params:
		`level`: Our own log record level
		`theme`: The theme
	@returns:
		The colors
	"""
	level = level.upper()
	for key, val in theme.items():
		val = tuple(val)
		if key == level:
			return val
		if key.startswith('in:') and level in key[3:].split(','):
			return val
		if key.startswith('starts:') and level.startswith(key[7:]):
			return val
		if key.startswith('has:') and key[4:] in level:
			return val
		if key.startswith('re:') and re.search(key[3:], level):
			return val
	return tuple(theme.get('',  (Fore.WHITE, Fore.WHITE)))
	
def _formatTheme(theme):
	"""
	Make them in the standard form with bgcolor and fgcolor in raw terminal color strings
	If the theme is read from file, try to translate "Fore.XXX", "Back.XXX" and "Style.XXX" 
	to terminal color strings
	@params:
		`theme`: The theme
	@returns:
		The formatted colors
	"""
	if theme is True:
		theme = THEMES['greenOnBlack']
	if not theme:
		return False
	if not isinstance(theme, dict):
		raise LoggerThemeError(theme, 'No such theme')
	
	ret = theme.copy()
	ret[''] = ret.get('', [Fore.WHITE] * 2)
	for key, val in theme.items():
		if not isinstance(val, (tuple, list)):
			val = [val]
		if len(val) == 1:
			val = val * 2

		for i, v in enumerate(val):
			t = TemplateLiquid(v, Fore = Fore, Back = Back, Style = Style)
			val[i] = t.render()

		ret[key] = val
	return ret
	
class PyPPLLogFilter (logging.Filter):
	"""
	logging filter by levels (flags)
	"""
	
	def __init__(self, name='', lvls='normal', lvldiff=None):
		"""
		Constructor
		@params:
			`name`: The name of the logger
			`lvls`: The levels of records to keep
			`lvldiff`: The adjustments to `lvls`
		"""

		logging.Filter.__init__(self, name)
		self.debugs = {key: 0 for key, _ in DEBUG_LINES.items()}
		self.levels = []
		
		if lvls is not None:
			if not isinstance(lvls, list):
				if lvls in LEVELS:
					self.levels += LEVELS[lvls]
				elif lvls == 'ALL':
					self.levels += LEVELS['all']
				elif lvls:
					self.levels += [lvls]
				elif lvls is False:
					return
			else:
				self.levels += lvls

			self.levels += LEVELS_ALWAYS
			
		lvldiff = lvldiff or []
		if not isinstance(lvldiff, list):
			lvldiff = [lvldiff]
		for ld in lvldiff:
			if ld.startswith('-'):
				ld = ld[1:].upper()
				if ld in self.levels: 
					del self.levels[self.levels.index(ld)]
			elif ld.startswith('+'):
				ld = ld[1:].upper()
				if ld not in self.levels:
					self.levels.append(ld)
			else:
				ld = ld.upper()
				if ld not in self.levels:
					self.levels.append(ld)
	
	def filter (self, record):
		"""
		Filter the record
		@params:
			`record`: The record to be filtered
		@return:
			`True` if the record to be kept else `False`
		"""
		level = record.loglevel.upper() if hasattr(record, 'loglevel') else record.levelname
		if level.startswith('_'):
			return True
		if not self.levels:
			return False
		if level in self.levels:
			level2 = record.level2 if hasattr(record, 'level2') else None
			if not level2 or level2 not in DEBUG_LINES:
				return True
			self.debugs[level2] += 1
			if self.debugs[level2] <= abs(DEBUG_LINES[level2]):
				if DEBUG_LINES[level2] < 0 and self.debugs[level2] == abs(DEBUG_LINES[level2]):
					record.msg += "\n...... max={max} ({key}) reached, further information will be ignored.".format(max = abs(DEBUG_LINES[level2]), key = level2)
				return True
		return False

class PyPPLLogFormatter (logging.Formatter):
	"""
	logging formatter for pyppl
	"""
	def __init__(self, fmt=None, theme='greenOnBlack', secondary = False):
		"""
		Constructor
		@params:
			`fmt`      : The format
			`theme`    : The theme
			`secondary`: Whether this is a secondary formatter or not (another formatter applied before this).
		"""
		fmt = LOGFMT if fmt is None else fmt
		logging.Formatter.__init__(self, fmt, "%Y-%m-%d %H:%M:%S")
		self.theme     = theme
		# whether it's a secondary formatter (for fileHandler)
		self.secondary = secondary
		
	def format(self, record):
		"""
		Format the record
		@params:
			`record`: The log record
		@returns:
			The formatted record
		"""
		if not hasattr(record, 'raw'):
			setattr(record, 'raw', record.msg)

		level = record.loglevel.upper() if hasattr(record, 'loglevel') else record.levelname

		theme = 'greenOnBlack' if self.theme is True else self.theme
		theme = THEMES[theme] if not isinstance(theme, dict) and theme in THEMES else theme
		theme = _formatTheme(theme)

		if not theme:
			colorLevelStart = ''
			colorMsgStart   = ''
			colorLevelEnd   = ''
		else:
			(colorLevelStart, colorMsgStart) = _getColorFromTheme(level, theme)
			colorLevelEnd   = Style.RESET_ALL
		
		if self.secondary:
			# keep _ for file handler
			level = level[1:] if level.startswith('_') else level
		level = level[:7]
		record.msg = " {lstart_c}{level}{lend_c}] {mstart_c}{proc}{jobindex}{msg}{lend_c}".format(
			lstart_c = colorLevelStart,
			level    = level.rjust(7),
			lend_c   = colorLevelEnd,
			mstart_c = colorMsgStart,
			proc     = '{}: '.format(record.proc) if hasattr(record, 'proc') else '',
			jobindex = '[{ji}/{jt}] '.format(ji = str(record.jobidx + 1).zfill(len(str(record.joblen))), jt = record.joblen) if hasattr(record, 'jobidx') else '',
			msg      = record.raw)
		return logging.Formatter.format(self, record)

class PyPPLStreamHandler(logging.StreamHandler):
	"""
	PyPPL stream log handler.
	To implement the progress bar for JOBONE and SUBMIT logs.
	"""

	#PREVBAR = MANAGER.list([''])

	def __init__(self, stream = None):
		"""
		Constructor
		@params:
			`stream`: The stream
		"""
		super(PyPPLStreamHandler, self).__init__(stream)
		# Attribute 'terminator' defined outside __init__ (attribute-defined-outside-init)
		self.terminator = "\n"
		self.prevbar = None

	def _emit(self, record, terminator = "\n"):
		"""
		Helper function implementing a python2,3-compatible emit.
		Allow to add "\n" or "\r" as terminator.
		"""
		#terminator = '\n'
		if sys.version_info.major > 2: # pragma: no cover
			self.terminator = terminator
			super(PyPPLStreamHandler, self).emit(record)
		else:
			msg = self.format(record)
			stream = self.stream
			fs = "%s" + terminator
			#if no unicode support...
			if not logging._unicode: # pragma: no cover
				stream.write(fs % msg)
			else:
				try:
					if (isinstance(msg, unicode) and
						getattr(stream, 'encoding', None)): # pragma: no cover
						ufs = u'%s' + terminator
						try:
							stream.write(ufs % msg)
						except UnicodeEncodeError:
							#Printing to terminals sometimes fails. For example,
							#with an encoding of 'cp1251', the above write will
							#work if written to a stream opened or wrapped by
							#the codecs module, but fail when writing to a
							#terminal even when the codepage is set to cp1251.
							#An extra encoding step seems to be needed.
							stream.write((ufs % msg).encode(stream.encoding))
					else:
						stream.write(fs % msg)
				except UnicodeError: # pragma: no cover
					stream.write(fs % msg.encode("UTF-8"))
			self.flush()

	def emit(self, record):
		"""
		Emit the record.
		"""
		from .jobmgr import Jobmgr
		try:
			pbar = record.pbar if hasattr(record, 'pbar') else None
			if pbar == 'next':
				if self.prevbar:
					self.stream.write("\n")
				self._emit(record, "\n")
			elif pbar is None:
				# break pbars
				if not "\n" in record.msg:
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						rec.msg = m
						if i == len(msgs) - 1 and m.startswith('...... max='):
							delattr(rec, 'jobidx')
						self._emit(rec, "\n")
				self.prevbar = None
			elif pbar is True:
				# pbar, replace previous pbar
				self.prevbar = record
				self._emit(record, "\r")
			elif not self.prevbar:
				# not pbar and not prev pbar
				justlen = Jobmgr.PBAR_SIZE + 32
				if hasattr(record, 'proc'):
					justlen += len(record.proc) + 2
				if hasattr(record, 'jobidx'):
					justlen += len(str(record.joblen)) * 3
				justlen = max(justlen, Jobmgr.PBAR_SIZE + 32)
				if not "\n" in record.msg:
					record.msg = record.msg.ljust(justlen)
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						if i == len(msgs) - 1 and m.startswith('...... max='):
							rec.msg = m.ljust(justlen)
							delattr(rec, 'jobidx')
						else:
							rec.msg = m.ljust(justlen)
						self._emit(rec, "\n")
			else:
				# not pbar but prev pbar
				justlen = Jobmgr.PBAR_SIZE + 32
				if hasattr(self.prevbar, 'proc'):
					justlen += len(self.prevbar.proc) + 2
				if hasattr(self.prevbar, 'jobidx'):
					justlen += len(str(self.prevbar.joblen)) * 3
				justlen = max(justlen, Jobmgr.PBAR_SIZE + 32)
				if not "\n" in record.msg:
					record.msg = record.msg.ljust(justlen)
					self._emit(record, "\n")
				else:
					msgs = record.msg.splitlines()
					for i, m in enumerate(msgs):
						rec = pycopy(record)
						if i == len(msgs) - 1 and m.startswith('...... max='):
							rec.msg = m.ljust(justlen)
							delattr(rec, 'jobidx')
						else:
							rec.msg = m.ljust(justlen)
						self._emit(rec, "\n")
				self._emit(self.prevbar, "\r")
		except (KeyboardInterrupt, SystemExit, IOError, EOFError): # pragma: no cover
			raise
		except Exception: # pragma: no cover
			self.handleError(record)

def getLogger (levels='normal', theme=True, logfile=None, lvldiff=None, name='PyPPL'):
	"""
	Get the default logger
	@params:
		`levels`: The log levels(tags), default: basic
		`theme`:  The theme of the logs on terminal. Default: True (default theme will be used)
			- False to disable theme
		`logfile`:The log file. Default: None (don't white to log file)
		`lvldiff`:The diff levels for log
			- ["-depends", "jobdone", "+debug"]: show jobdone, hide depends and debug
		`name`:   The name of the logger, default: PyPPL
	@returns:
		The logger
	"""
	logger = logging.getLogger (name)
	for handler in logger.handlers:
		handler.close()
	del logger.handlers[:]
	
	if logfile:
		fileCh = logging.FileHandler(logfile)
		fileCh.setFormatter(PyPPLLogFormatter(theme = None))
		logger.addHandler (fileCh)
		
	streamCh  = PyPPLStreamHandler()
	formatter = PyPPLLogFormatter(theme = theme, secondary = True)
	filter_   = PyPPLLogFilter(name = name, lvls = levels, lvldiff = lvldiff)
	streamCh.addFilter(filter_)
	streamCh.setFormatter(formatter)
	logger.addHandler (streamCh)
	
	logger.setLevel(1)
	# Output all logs
	return logger
	
logger = getLogger()
