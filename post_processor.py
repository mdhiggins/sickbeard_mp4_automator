import os
from subprocess import Popen, PIPE

bad_files = ['resources', '.DS_Store']

class PostProcessor:
	def __init__(self, output):
		self.output = output
		print 'output'
		print output
		self.set_script_environment()
		# self.post_process_environment = os.environ.copy()
		# self.post_process_environment['output'] = str(self.output)
		self.scripts = []
		self.gather_scripts()
	def set_script_environment(self):
		print 'set script environment'
		self.post_process_environment = os.environ.copy()
		for key, value in self.output.iteritems():
			print 'key: ' + str(key)
			print 'value: ' + str(value)
			self.post_process_environment[str(key)] = str(value)
	def gather_scripts(self):
		print 'gather scripts'
		current_directory = os.path.dirname(os.path.realpath(__file__))
		post_process_directory = os.path.join(current_directory, 'post_process')
		for script in os.listdir(post_process_directory):
			if script.endswith('.pyc') or os.path.isdir(script) or (script in bad_files):
				continue
			else:
				self.scripts.append(os.path.join(post_process_directory, script))
	def run_scripts(self):
		print 'run scripts'
		for script in self.scripts:
			try:
				print 'script: ' + str(script)
				command = self.run_script_command(script)
				print 'command ->'
				print command
				print str(command)
				stdout, stderr = command.communicate()
				print stdout
				print stderr
			except Exception as e:
				print 'tried to run script ' + str(script)
				print e
	def run_script_command(self, script):
		print 'script command getter'
		print script
		print type(script)
		return Popen([str(script)], shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=self.post_process_environment,
                     close_fds=(os.name != 'nt'))