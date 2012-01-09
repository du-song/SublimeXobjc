import sublime
import sublime_plugin
import re
import os.path
import xobjc

class XobjcCommandQueue(sublime_plugin.EventListener):
	pending = {}
	command = None
	def set_command(self, command):
		self.command = command

	def on_load(self, view):
		print self.command
		buffer_id = self.pending.get(view.buffer_id())
		if buffer_id:
			(v1, v2) = self.pending[view.buffer_id()]
			del self.pending[view.buffer_id()]
			self.command._run(v1, v2)

	def on_close(self, view):
		buffer_id = self.pending.get(view.buffer_id())
		if buffer_id:
			del self.pending[view.buffer_id()]
		#FIXME may be buggy if close view1 too soon

class XobjcCommand(sublime_plugin.TextCommand):
	queue = None
	def is_enabled(self):
		f = self.view.file_name();
		return f and f.endswith(("m", "h")); # for .h .m .mm

	def run(self, edit):
		v1 = self.view
		f1 = v1.file_name()
		if f1.endswith("h"):
			f2 = os.path.splitext(f1)[0] + ".mm"
			if not os.path.isfile(f2): f2 = os.path.splitext(f1)[0] + ".m"
		else:
			f2 = os.path.splitext(f1)[0] + ".h"
		v2 = v1.window().open_file(f2) #, sublime.TRANSIENT
		v2.window().focus_view(v1)
		if v2.is_loading():
			if not self.queue:
				self.queue = XobjcCommandQueue()
				self.queue.set_command(self)
			print self.queue.command
			self.queue.pending[v2.buffer_id()] = (v1, v2)
		else:
			self._run(v1, v2);

	def _run(self, view_h, view_m):
		settings = view_h.settings()
		xobjc.BACKUP_FOLDER = settings.get("xobjc_backup_folder") or os.path.expandvars('${HOME}/work/_build/__xobjc_backup') #not in use
		xobjc.BOOL_WITH_IS_GETTER = settings.get("xobjc_bool_getter_with_is") or False
		xobjc.NONATOMIC = settings.get("xobjc_nonatomic_text") or "nonatomic, "
		xobjc.INDENTATION = " "*int(settings.get("tab_size")) if settings.get("translate_tabs_to_spaces") else "\t"

		if view_h.file_name().endswith("m"): (view_h, view_m) = (view_m, view_h)
		region_h = sublime.Region(0, view_h.size())
		code_h   = view_h.substr(region_h)
		region_m = sublime.Region(0, view_m.size())
		code_m   = view_m.substr(region_m)
		(new_h, new_m) = xobjc.analyze(code_h, code_m)
		updated = False
		if new_h and new_h != code_h:
			try:
				edit = view_h.begin_edit()
				view_h.replace(edit, region_h, new_h)
				updated = True
			finally:
				view_h.end_edit(edit)
		if new_m and new_m != code_m:
			try:
				edit = view_m.begin_edit()
				view_m.replace(edit, region_m, new_m)
				updated = True
			finally:
				view_m.end_edit(edit)
		if updated:
			sublime.status_message("Xobjc: code has been updated")
		else:
			sublime.status_message("Xobjc: no updated needed")

