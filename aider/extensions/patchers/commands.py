import subprocess
import sys
from aider.commands import Commands
from aider.extensions.file_changer_gui.start_gui import AiderFileGUIApp

def apply_patch():
    def add_cmd_helloworld():
        def cmd_helloworld(self, args):
            "Output Hello"
            self.io.tool_output("Hello")

        setattr(Commands, 'cmd_helloworld', cmd_helloworld)

    def add_cmd_filegui():
        def cmd_filegui(self, args):
            "Start the file GUI based on the coder root path"
            try:
                command = [sys.executable, '-c', 
                           'from aider.extensions.file_changer_gui.start_gui import AiderFileGUIApp; '
                           'from PyQt5.QtWidgets import QApplication; '
                           f'app = QApplication([]); ex = AiderFileGUIApp("{self.coder.root}"); ex.show(); app.exec_()']
            
                subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
            except Exception as e:
                # Silently handle any exceptions
                pass

        setattr(Commands, 'cmd_filegui', cmd_filegui)

    def add_silent_commands():
        def cmd_drop_silent(self, args):
            "Silently drop files from the chat session"
            original_tool_output = self.io.tool_output
            self.io.tool_output = lambda *args, **kwargs: None
            try:
                self.cmd_drop(args)
            except Exception as e:
                original_tool_output(f"Error: {str(e)}")
            finally:
                self.io.tool_output = original_tool_output

        def cmd_add_silent(self, args):
            "Silently add files to the chat session"
            original_tool_output = self.io.tool_output
            self.io.tool_output = lambda *args, **kwargs: None
            try:
                self.cmd_add(args)
            except Exception as e:
                original_tool_output(f"Error: {str(e)}")
            finally:
                self.io.tool_output = original_tool_output

        def cmd_read_only_silent(self, args):
            "Silently add read-only files to the chat session"
            original_tool_output = self.io.tool_output
            self.io.tool_output = lambda *args, **kwargs: None
            try:
                self.cmd_read_only(args)
            except Exception as e:
                original_tool_output(f"Error: {str(e)}")
            finally:
                self.io.tool_output = original_tool_output

        setattr(Commands, 'cmd_drop_silent', cmd_drop_silent)
        setattr(Commands, 'cmd_add_silent', cmd_add_silent)
        setattr(Commands, 'cmd_read_only_silent', cmd_read_only_silent)

    add_cmd_helloworld()
    add_cmd_filegui()
    add_silent_commands()
