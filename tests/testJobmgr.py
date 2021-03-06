import helpers, testly, sys
from os import path, makedirs
from shutil import rmtree
from tempfile import gettempdir

from pyppl import Proc
from pyppl.jobmgr import Jobmgr

# just high-level tests
class TestJobmgr(testly.TestCase):
	
	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestJobmgr')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def testJmNoJobs(self):
		pNoJobs = Proc()
		pNoJobs.nthread = 1
		pNoJobs.run()

	def testJm1(self):
		p = Proc()
		p.script = 'echo 123'
		p.forks  = 1
		p.nthread = 1
		p.input = {'a': [1, 2]}
		p.run()

	def testJm2(self):
		oPBAR_SIZE = Jobmgr.PBAR_SIZE
		Jobmgr.PBAR_SIZE = 10
		p1 = Proc()
		p1.script = 'echo 123'
		p1.forks = Jobmgr.PBAR_SIZE * 2
		p1.nthread = 1
		p1.input = {'a': list(range(Jobmgr.PBAR_SIZE * 2))}
		p1.run()
		Jobmgr.PBAR_SIZE = oPBAR_SIZE

	# whole test process will be killed.
	# def testJm3(self):
	# 	p2 = Proc()
	# 	p2.script = '__err__ 123'
	# 	p2.forks = 20
	# 	p2.nthread = 1
	# 	p2.input = {'a': list(range(20))}
	# 	p2.errhow = 'halt'
	# 	try:
	# 		p2.run()
	# 	except SystemExit:
	# 		pass

	def testJm4(self):
		from time import time
		p3         = Proc()
		p3.forks   = 1
		p3.nthread    = 1
		p3.lang    = sys.executable
		p3.args.i  = time()
		p3.input   = {'a': [0]}
		p3.errntry = 10
		p3.errhow  = 'retry'
		p3.script  = '''#
		# PYPPL INDENT REMOVE
		from time import sleep, time
		sleep(.1)
		t = time() - {{args.i}}
		if t < 1:
			exit(1)
		'''
		p3.run()

	
if __name__ == '__main__':
	testly.main(verbosity=2)
