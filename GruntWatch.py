from os import path
import os
import re
import sublime
ExecCommand = __import__('exec').ExecCommand


if os.name == 'nt':
	GRUNT_CMD = 'grunt.cmd'
else:
	GRUNT_CMD = 'grunt'


def settings():
	return sublime.load_settings('GruntWatch.sublime-settings')


class GruntWatchCommand(ExecCommand):
	def run(self, *args, **kwarg):
		self.started = False

		root_dir = self.project_root()
		if not root_dir:
			sublime.status_message('Gruntfile not found.')
			return

		if kwarg.get('kill', False):
			sublime.status_message('Stopping Grunt...')
		else:
			sublime.status_message('Starting Grunt...')

		file_regex = settings().get('file_regex')
		if file_regex:
			file_regex = '(?:%s)' % '|'.join(file_regex)
		else:
			file_regex = ''
		grunt_args = settings().get('grunt_args', '')

		kwarg['cmd'] = [u'%s watch --no-color %s' % (GRUNT_CMD, grunt_args)]
		kwarg['shell'] = True
		#kwarg['quiet'] = True
		kwarg['file_regex'] = file_regex
		kwarg['working_dir'] = root_dir

		skip_regex = settings().get('skip_regex')
		if skip_regex:
			self.skip_regex = re.compile('(?:%s)' % '|'.join(skip_regex))

		super(GruntWatchCommand, self).run(*args, **kwarg)
		self.window.run_command('hide_panel', {'panel': 'output.exec'})

	def append_data(self, proc, data):
		if proc != self.proc:
			# a second call to exec has been made before the first one
			# finished, ignore it instead of intermingling the output.
			if proc:
				proc.kill()
			return

		try:
			str = data.decode(self.encoding)
		except:
			str = '[Decode error - output not %s]\n' % self.encoding
		proc = None

		# Normalize newlines, Sublime Text always uses a single \n separator
		# in memory.
		str = str.replace('\r\n', '\n').replace('\r', '\n')

		print '[[%s]]' % str

		if str == 'Waiting...' and not self.started:
			self.started = True
			sublime.status_message('Grunt watching...')
			return

		lines = str.split('\n')
		msg = []
		for line in lines:
			if line.startswith('>>'):
				msg.append(re.sub(r'^>>\s*', r'', line))
			else:
				if len(msg):
					msg = '\n'.join(msg)
					if not self.skip_regex.match(msg):
						self.show_error_panel(msg)
					msg = []
				m = re.match(r'<(?:WARN|FATAL)>(.*?)</(?:WARN|FATAL)>', line)
				if m:
					self.show_error_panel(m.group(1))

	def finish(self, proc):
		if proc == self.proc:
			sublime.status_message('Grunt stopped')
		super(GruntWatchCommand, self).finish(proc)

	def project_root(self):
		dir = self.window.active_view().file_name()
		while True:
			parent = path.realpath(path.join(dir, '..'))
			if parent == dir:  # System root folder
				break
			dir = parent
			if path.isfile(path.join(dir, 'grunt.js')):
				return dir
		return None

	def show_error_panel(self, str):
		str = str + '\n'
		selection_was_at_end = (len(self.output_view.sel()) == 1
			and self.output_view.sel()[0]
				== sublime.Region(self.output_view.size()))
		self.output_view.set_read_only(False)
		edit = self.output_view.begin_edit()
		self.output_view.insert(edit, self.output_view.size(), str)
		if selection_was_at_end:
			self.output_view.show(self.output_view.size())
		self.output_view.end_edit(edit)
		self.output_view.set_read_only(True)

		self.window.run_command('show_panel', {'panel': 'output.exec'})
