import os
from subprocess import Popen, PIPE

class PostProcessor:
	def __init__(self, output):
		self.output = output
		print 'output'
		print output
		self.post_process_environment = os.environ.copy()
		self.post_process_environment['output'] = self.output
		self.scripts = []
		self.gather_scripts()
	def gather_scripts(self):
		print 'gather scripts'
		current_directory = os.path.dirname(os.path.realpath(__file__))
		post_process_directory = os.path.join(current_directory, 'post_process')
		for script in os.listdir(post_process_directory):
			if script.endswith('.pyc') or (script == 'resources'):
				continue
			else:
				self.scripts.append(os.path.join(post_process_directory, script))
	def run_scripts(self):
		print 'run scripts'
		for script in self.scripts:
			try:
				print 'script: ' + str(script)
				command = self.run_script_command(script)
				command.communicate()
			except Exception as e:
				print 'try to run script ' + str(script)
				print e
	def run_script_command(self, script):
		return Popen([script], shell=False, stdin=PIPE, stdout=PIPE, env=self.post_process_environment, stderr=PIPE,
                     close_fds=(os.name != 'nt'))