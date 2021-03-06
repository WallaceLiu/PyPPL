import helpers, testly, unittest, sys

from os import path, getcwd, makedirs, remove
from shutil import rmtree
from tempfile import gettempdir
from hashlib import md5
from collections import OrderedDict
from subprocess import list2cmdline
from pyppl import Job, utils, runners
from pyppl.runners import Runner, RunnerLocal, RunnerDry, RunnerSsh, RunnerSge, RunnerSlurm
from pyppl.template import TemplateLiquid
from pyppl.exception import RunnerSshError
#from pyppl.runners.helpers import Helper, LocalHelper, SgeHelper, SlurmHelper, SshHelper

__here__ = path.realpath(path.dirname(__file__))

def clearMockQueue():
	qsubQfile   = path.join(__here__, 'mocks', 'qsub.queue.txt')
	sbatchQfile = path.join(__here__, 'mocks', 'sbatch.queue.txt')
	helpers.writeFile(qsubQfile, '')
	helpers.writeFile(sbatchQfile, '')

def createJob(testdir, index = 0, config = None):
	config = config or {}
	config['workdir']  = testdir
	config['procsize'] = config.get('procsize', 1)
	config['proc']     = config.get('proc', 'pTestRunner')
	config['tag']      = config.get('tag', 'notag')
	config['suffix']   = config.get('suffix', 'suffix')
	jobdir = path.join(testdir, str(index+1))
	if not path.exists(jobdir):
		makedirs(jobdir)
	with open(path.join(jobdir, 'job.script'), 'w') as f:
		f.write('#!/usr/bin/env bash')
		f.write(config.get('_script', ''))
	open(path.join(jobdir, 'job.stdout'), 'w').close()
	open(path.join(jobdir, 'job.stderr'), 'w').close()
	return Job(index, config)

class TestRunner(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunner')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(path.join(self.testdir, 'pTestInit')),

	def testInit(self, job):
		r = Runner(job)
		self.assertIsInstance(r, Runner)
		self.assertIs(r.job, job)
		self.assertEqual(r.script, [job.script])
		self.assertEqual(r.cmd2run, job.script)
	
	def dataProvider_testIsRunning(self):
		yield createJob(path.join(self.testdir, 'pTestIsRunning'), 0), False

		job1 = createJob(path.join(self.testdir, 'pTestIsRunning'), 1)
		r = utils.cmd.run('sleep 10', bg = True)
		job1.pid = r.pid
		yield job1, True

	def testIsRunning(self, job, ret):
		r = Runner(job)
		self.assertEqual(r.isRunning(), ret)
		if ret:
			r.kill()
			self.assertEqual(r.isRunning(), False)
	
	def dataProvider_testSubmit(self):
		job = createJob(path.join(self.testdir, 'pTestSubmit'))
		yield job, [
			sys.executable,
			path.realpath(runners.runner.__file__),
			job.script
		]

	def testSubmit(self, job, cmd):
		r = Runner(job)
		self.assertEqual(r.submit().cmd, list2cmdline(cmd))

	# Covered by job.run
	# def dataProvider_testRun(self):
	# 	job = createJob(path.join(self.testdir, 'pTestRun'), config = {
	# 		'echo': {'jobs': [0], 'type': {'stderr': None, 'stdout': None}}
	# 	})
	# 	yield job, 

	# def testRun(self, job, stdout = '', stderr = ''):
	# 	r = Runner(job)
	# 	r.submit()
	# 	r.run()
	# 	with open(job.outfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), stdout)
	# 	with open(job.errfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), stderr)
	# 	with open(job.rcfile, 'r') as f:
	# 		self.assertEqual(f.read().strip(), '0')


class TestLocalSubmitter(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestLocalSubmitter')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testInit(self):
		yield path.join(self.testdir, 'pTestInit', '1', 'job.script'),

	def testInit(self, script):
		ls = runners.runner._LocalSubmitter(script)
		scriptdir = path.dirname(script)
		self.assertEqual(ls.script, script)
		self.assertEqual(ls.rcfile, path.join(scriptdir, 'job.rc'))
		self.assertEqual(ls.pidfile, path.join(scriptdir, 'job.pid'))
		self.assertEqual(ls.outfile, path.join(scriptdir, 'job.stdout'))
		self.assertEqual(ls.errfile, path.join(scriptdir, 'job.stderr'))
		self.assertEqual(ls.outfd, None)
		self.assertEqual(ls.errfd, None)

	def dataProvider_testSubmit(self):
		script1 = path.join(self.testdir, 'pTestInit', '1', 'job.script')
		makedirs(path.dirname(script1))
		with open(script1, 'w') as f:
			f.write('#!/usr/bin/env bash\necho 1\necho 2 >&2')
		yield runners.runner._LocalSubmitter(script1), script1, '1', '2'

	def testSubmit(self, ls, cmd, stdout = '', stderr = ''):
		ls.submit()
		ls.quit()
		self.assertEqual(ls.proc.rc, 0)
		self.assertEqual(ls.proc.cmd, cmd)
		with open(ls.outfile, 'r') as f:
			self.assertEqual(f.read().strip(), stdout)
		with open(ls.errfile, 'r') as f:
			self.assertEqual(f.read().strip(), stderr)
		with open(ls.rcfile, 'r') as f:
			self.assertEqual(f.read().strip(), '0')

	def dataProvider_testMain(self):
		script2 = path.join(self.testdir, 'pTestInit', '2', 'job.script')
		makedirs(path.dirname(script2))
		with open(script2, 'w') as f:
			f.write('#!/usr/bin/env bash\necho 1\necho 2 >&2')
		yield script2, '1', '2'

	def testMain(self, script, stdout = '', stderr = ''):
		cmd = [sys.executable, runners.runner.__file__, script]
		utils.cmd.run(cmd)
		scriptdir = path.dirname(script)
		rcfile  = path.join(scriptdir, 'job.rc')
		pidfile = path.join(scriptdir, 'job.pid')
		outfile = path.join(scriptdir, 'job.stdout')
		errfile = path.join(scriptdir, 'job.stderr')
		with open(outfile, 'r') as f:
			self.assertEqual(f.read().strip(), stdout)
		with open(errfile, 'r') as f:
			self.assertEqual(f.read().strip(), stderr)
		with open(rcfile, 'r') as f:
			self.assertEqual(f.read().strip(), '0')
	
class TestRunnerLocal(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerLocal')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		job = createJob(
			self.testdir, 
			config = {
				'runnerOpts': {
					'localRunner': {'preScript': 'prescript', 'postScript': 'postscript'}
				}
			}
		)
		yield job, '#!/usr/bin/env bash\nprescript\n\n{}\n\npostscript'.format(job.script)

	def testInit(self, job, content):
		r = RunnerLocal(job)
		self.assertIsInstance(r, RunnerLocal)
		self.assertEqual(r.script, job.script + '.local')
		self.assertTrue(path.exists(r.script))
		with open(r.script, 'r') as f:
			self.assertEqual(f.read().strip(), content)

class TestRunnerDry(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerDry')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)

	def dataProvider_testInit(self):
		job = createJob(self.testdir)
		job.output = {
			'a' : {'type': 'file', 'data': 'a.txt'},
			'b' : {'type': 'dir' , 'data': 'b.dir'},
			'c' : {'type': 'var' , 'data': 'c'}
		}
		yield job, "#!/usr/bin/env bash\n\ntouch 'a.txt'\nmkdir -p 'b.dir'"

	def testInit(self, job, content):
		r = RunnerDry(job)
		self.assertIsInstance(r, RunnerDry)
		self.assertEqual(r.script, job.script + '.dry')
		self.assertTrue(path.exists(r.script))
		with open(r.script, 'r') as f:
			self.assertEqual(f.read().strip(), content)

class TestRunnerSsh(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSsh')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)		
	
	def dataProvider_testIsServerAlive(self):
		yield 'noalive', None, False
		yield 'blahblah', None, False
	
	def testIsServerAlive(self, server, key, ret):
		self.assertEqual(RunnerSsh.isServerAlive(server, key), ret)
		
	def dataProvider_testInit(self):
		yield createJob(
			self.testdir
		), RunnerSshError, 'No server found for ssh runner.'
		
		servers = ['server1', 'server2', 'localhost']
		keys    = ['key1', 'key2', None]
		yield createJob(
			self.testdir,
			index = 1,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False,
			}}}
		),
		
		yield createJob(
			self.testdir,
			index = 2,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False
			}}}
		),
		
		yield createJob(
			self.testdir,
			index = 3,
			config = {'runnerOpts': {'sshRunner': {
				'servers': servers,
				'keys'   : keys,
				'checkAlive': False,
				'preScript': 'ls',
				'postScript': 'ls',
			}}}
		),
		# 4
		if RunnerSsh.isServerAlive('localhost', None, 1):
			# should be localhost'
			yield createJob(
				self.testdir,
				index = 4,
				config = {'runnerOpts': {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': 1
				}}}
			),
		else:
			yield createJob(
				self.testdir,
				index = 4,
				config = {'runnerOpts': {'sshRunner': {
					'servers': servers,
					'keys'   : keys,
					'checkAlive': 1
				}}}
			), RunnerSshError, 'No server is alive.'
		
		# no server is alive
		yield createJob(
			self.testdir,
			index = 5,
			config = {'runnerOpts': {'sshRunner': {
				'servers': ['server1', 'server2', 'server3'],
				'checkAlive': True,
			}}}
		), RunnerSshError, 'No server is alive.'

	def testInit(self, job, exception = None, msg = None):
		self.maxDiff = None
		RunnerSsh.LIVE_SERVERS = None
		if exception:
			self.assertRaisesRegex(exception, msg, RunnerSsh, job)
		else:
			r = RunnerSsh(job)
			servers = job.config['runnerOpts']['sshRunner']['servers']
			keys = job.config['runnerOpts']['sshRunner']['keys']

			sid = RunnerSsh.LIVE_SERVERS[job.index % len(RunnerSsh.LIVE_SERVERS)]
			server = servers[sid]
			key = ('-i ' + keys[sid]) if keys[sid] else ''
			self.assertIsInstance(r, RunnerSsh)
			self.assertTrue(path.exists(job.script + '.ssh'))
			#self.assertTrue(path.exists(job.script + '.submit'))
			preScript  = job.config['runnerOpts']['sshRunner'].get('preScript', '')
			preScript  = preScript and preScript + '\n'
			postScript = job.config['runnerOpts']['sshRunner'].get('postScript', '')
			postScript = postScript and '\n' + postScript
			helpers.assertTextEqual(self, helpers.readFile(job.script + '.ssh', str), '\n'.join([
				"#!/usr/bin/env bash",
				"# run on server: {}".format(server),
				"",
				'%scd %s; %s%s',
			]) % (
				preScript, 
				getcwd(), 
				job.script, 
				postScript
			) + '\n')
		
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
				}},
			}
		)
		yield job0, [
			path.join(__here__, 'mocks', 'ssh'), 
			list2cmdline([
				sys.executable, 
				path.realpath(runners.runner.__file__) if not runners.runner.__file__.endswith('c') else path.realpath(runners.runner.__file__)[:-1], 
				job0.script + '.ssh'
			])
		]
		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': 1,
				}},
			}
		)
		yield job1, [
			path.join(__here__, 'mocks', 'ssh'), 
			list2cmdline([
				sys.executable, 
				path.realpath(runners.runner.__file__) if not runners.runner.__file__.endswith('c') else path.realpath(runners.runner.__file__)[:-1], 
				job1.script + '.ssh'
			])
		]
		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
				}},
			}
		)
		yield job2, [
			path.join(__here__, 'mocks', 'ssh'), 
			list2cmdline([
				'ls',
				job2.script + '.ssh'
			])
		], 1
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSsh.INTERVAL = .1
		RunnerSsh.LIVE_SERVERS = None
		if job.config['runnerOpts']['sshRunner']['checkAlive'] and not RunnerSsh.isServerAlive('localhost', timeout = 1):
			self.assertRaises(RunnerSshError, RunnerSsh, job)
		else:
			r = RunnerSsh(job)
			if rc == 1:
				remove(r.script)
			r.sshcmd = [path.join(__here__, 'mocks', 'ssh')]
			c = r.submit()
			self.assertEqual(c.rc, rc)
			self.assertEqual(c.cmd, list2cmdline(cmd))

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sshRunner': {
					'servers': ['server1', 'server2', 'localhost'],
					'checkAlive': False,
				}},
				'_script': 'sleep 3; sleep 3 &'
			}
		)
		yield job0, 
	
	def testKill(self, job):
		RunnerSsh.INTERVAL = .1
		RunnerSsh.LIVE_SERVERS = None
		r = RunnerSsh(job)
		r.sshcmd = [path.join(__here__, 'mocks', 'ssh')]
		self.assertFalse(r.isRunning())
		r.job.pid = r.submit().pid
		self.assertTrue(r.isRunning())
		r.kill()
		self.assertFalse(r.isRunning())


class TestRunnerSge(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSge')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(
			self.testdir,
			config = {
				'runnerOpts': {'sgeRunner': {
					'sge.N': 'SgeJobName',
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.o': path.join(self.testdir, 'stdout'),
					'sge.e': path.join(self.testdir, 'stderr'),
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__here__, 'mocks', 'qsub')),
					'postScript': '',
					'qsub': 'qsub',
					'qstat': 'qstat',
					'qdel': 'qdel',
				}}
			}
		), 'SgeJobName', path.join(self.testdir, 'stdout'), path.join(self.testdir, 'stderr')
		
		yield createJob(
			self.testdir,
			index  = 1,
			config = {
				'runnerOpts': {'sgeRunner': {
					'sge.q': 'queue',
					'sge.j': 'y',
					'sge.M': 'xxx@abc.com',
					'sge.m': 'yes',
					'sge.mem': '4G',
					'sge.notify': True,
					'preScript': 'alias qsub="%s"' % (path.join(__here__, 'mocks', 'qsub')),
					'postScript': ''
				}}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = None
		r = RunnerSge(job)
		self.assertIsInstance(r, RunnerSge)
		self.assertEqual(r.script, job.script + '.sge')
		self.assertTrue(r.script)
		helpers.assertTextEqual(self, helpers.readFile(job.script + '.sge', str), '\n'.join([
			"#!/usr/bin/env bash",
			'#$ -N %s' % (jobname if jobname else '.'.join([
				job.config['proc'],
				job.config['tag'],
				job.config['suffix'],
				str(job.index + 1)
			])),
			'#$ -q queue',
			'#$ -j y',
			'#$ -o %s' % (outfile if outfile else job.outfile),
			'#$ -e %s' % (errfile if errfile else job.errfile),
			'#$ -cwd',
			'#$ -M xxx@abc.com',
			'#$ -m yes',
			'#$ -mem 4G',
			'#$ -notify',
			'',
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % job.rcfile,
			'alias qsub="%s"' % (path.join(__here__, 'mocks', 'qsub')),
			'',
			job.script,
			'',
			''
		]))
	
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job0, [
			path.join(__here__, 'mocks', 'qsub'), 
			job0.script + '.sge'
		]

		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'sbatch'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job1, [
			path.join(__here__, 'mocks', 'sbatch'), 
			job1.script + '.sge'
		], 1

		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', '_notexist_'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
			}
		)
		yield job2, [
			path.join(__here__, 'mocks', '_notexist_'), 
			job2.script + '.sge'
		], 1
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSge.INTERVAL = .1
		r = RunnerSge(job)
		c = r.submit()
		self.assertEqual(c.rc, rc)
		self.assertEqual(c.cmd, list2cmdline(cmd))

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', 'qstat'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
				'_script': 'sleep 3'
			}
		)
		yield job0, 

		job1 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'sgeRunner': {
					'preScript' : '',
					'postScript': '',
					'qsub'      : path.join(__here__, 'mocks', 'qsub'),
					'qstat'     : path.join(__here__, 'mocks', '_notexist_'),
					'qdel'      : path.join(__here__, 'mocks', 'qdel'),
				}},
				'_script': 'sleep 3'
			}
		)
		yield job1, False
	
	def testKill(self, job, beforekill = True):
		RunnerSge.INTERVAL = .1
		r = RunnerSge(job)
		self.assertFalse(r.isRunning())
		r.submit()
		self.assertEqual(r.isRunning(), beforekill)
		r.kill()
		self.assertFalse(r.isRunning())

class TestRunnerSlurm(testly.TestCase):

	def setUpMeta(self):
		self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestRunnerSlurm')
		if path.exists(self.testdir):
			rmtree(self.testdir)
		makedirs(self.testdir)
	
	def dataProvider_testInit(self):
		yield createJob(
			path.join(self.testdir, 'pTestInit'),
			config = {
				'runnerOpts': {'slurmRunner': {
					'slurm.J': 'SlurmJobName',
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.o': path.join(self.testdir, 'stdout'),
					'slurm.e': path.join(self.testdir, 'stderr'),
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'preScript': '',
					'postScript': '',
					'cmdPrefix': 'srun prefix',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}}
			}
		), 'SlurmJobName', path.join(self.testdir, 'stdout'), path.join(self.testdir, 'stderr')
		
		yield createJob(
			path.join(self.testdir, 'pTestInit'),
			index  = 1,
			config = {
				'runnerOpts': {'slurmRunner': {
					#'slurm.J': 'SlurmJobName',
					'slurm.q': 'queue',
					'slurm.j': 'y',
					'slurm.o': path.join(self.testdir, 'pTestInit', '2', 'job.stdout'),
					'slurm.e': path.join(self.testdir, 'pTestInit', '2', 'job.stderr'),
					'slurm.M': 'xxx@abc.com',
					'slurm.m': 'yes',
					'slurm.mem': '4G',
					'slurm.notify': True,
					'cmdPrefix': 'srun prefix',
					'preScript': '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}}
			}
		),
		
	def testInit(self, job, jobname = None, outfile = None, errfile = None):
		self.maxDiff = None
		r = RunnerSlurm(job)
		self.assertIsInstance(r, RunnerSlurm)
		self.assertEqual(r.script, job.script + '.slurm')
		self.assertTrue(r.script)
		helpers.assertTextEqual(self, helpers.readFile(job.script + '.slurm', str), '\n'.join([
			"#!/usr/bin/env bash",
			'#SBATCH -J %s' % (jobname if jobname else '.'.join([
				job.config['proc'],
				job.config['tag'],
				job.config['suffix'],
				str(job.index + 1)
			])),
			'#SBATCH -o %s' % (outfile if outfile else job.outfile),
			'#SBATCH -e %s' % (errfile if errfile else job.errfile),
			'#SBATCH -M xxx@abc.com',
			'#SBATCH -j y',
			'#SBATCH -m yes',
			'#SBATCH --mem 4G',
			'#SBATCH --notify',
			'#SBATCH -q queue',
			'',
			'trap "status=\\$?; echo \\$status >\'%s\'; exit \\$status" 1 2 3 6 7 8 9 10 11 12 15 16 17 EXIT' % job.rcfile,
			'',
			'',
			'srun prefix ' + job.script,
			'',
			''
		]))
	
	def dataProvider_testSubmit(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job0, [
			path.join(__here__, 'mocks', 'sbatch'), 
			job0.script + '.slurm'
		]

		job1 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 1,
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'qsub'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job1, [
			path.join(__here__, 'mocks', 'qsub'), 
			job1.script + '.slurm'
		], 1

		job2 = createJob(
			path.join(self.testdir, 'pTestSubmit'),
			index = 2,
			config = {
				'echo': {'jobs': [2], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', '_notexist_'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
			}
		)
		yield job2, [
			path.join(__here__, 'mocks', '_notexist_'), 
			job2.script + '.slurm'
		], 1
	
	def testSubmit(self, job, cmd, rc = 0):
		RunnerSlurm.INTERVAL = .1
		r = RunnerSlurm(job)
		c = r.submit()
		self.assertEqual(c.rc, rc)
		self.assertEqual(c.cmd, list2cmdline(cmd))

	def dataProvider_testKill(self):
		job0 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [0], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', 'squeue'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
				'_script': 'sleep 3'
			}
		)
		yield job0, 

		job1 = createJob(
			path.join(self.testdir, 'pTestKill'),
			config = {
				'echo': {'jobs': [1], 'type': {'stdout': None}},
				'runnerOpts': {'slurmRunner': {
					'preScript' : '',
					'postScript': '',
					'sbatch': path.join(__here__, 'mocks', 'sbatch'),
					'srun': path.join(__here__, 'mocks', 'srun'),
					'squeue': path.join(__here__, 'mocks', '_notexist_'),
					'scancel': path.join(__here__, 'mocks', 'scancel')
				}},
				'_script': 'sleep 3'
			}
		)
		yield job1, False
	
	def testKill(self, job, beforekill = True):
		RunnerSlurm.INTERVAL = .1
		r = RunnerSlurm(job)
		self.assertFalse(r.isRunning())
		r.submit()
		self.assertEqual(r.isRunning(), beforekill)
		r.kill()
		self.assertFalse(r.isRunning())


if __name__ == '__main__':
	clearMockQueue()
	testly.main(verbosity=2, failfast = True)
