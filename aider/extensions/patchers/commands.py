import os
import subprocess
import sys
import traceback
from aider.commands import Commands

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
                command = [
                    sys.executable,
                    f"{os.environ.get('PATH_AIDER', '')}/aider/extensions/file_changer_gui/start_gui.py",
                ]
            
                # Create detached process
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True  # This prevents the process from closing with parent
                )
                
                # Store process reference to ensure cleanup
                if not hasattr(self, '_gui_processes'):
                    self._gui_processes = []
                self._gui_processes.append(process)
                
                # Start a thread to handle output asynchronously
                def handle_output():
                    stdout, stderr = process.communicate()
                    if stdout:
                        print(f"GUI Output: {stdout.decode()}")
                    if stderr:
                        print(f"GUI Errors: {stderr.decode()}")
                
                import threading
                output_thread = threading.Thread(target=handle_output, daemon=True)
                output_thread.start()
                
            except Exception as e:
                traceback.print_exc()
                print(f"File GUI Error: {str(e)}")

        setattr(Commands, 'cmd_filegui', cmd_filegui)


    def add_silent_commands():
        def cmd_drop_silent(self, args):
            "Silently drop files from the chat session"
            original_tool_output = self.io.tool_output
            self.io.tool_output = lambda *args, **kwargs: None
            try:
                self.cmd_drop(args)
            except Exception as e:
                traceback.print_exc()
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
                traceback.print_exc()
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
                traceback.print_exc()
                original_tool_output(f"Error: {str(e)}")
            finally:
                self.io.tool_output = original_tool_output

        setattr(Commands, 'cmd_drop_silent', cmd_drop_silent)
        setattr(Commands, 'cmd_add_silent', cmd_add_silent)
        setattr(Commands, 'cmd_read_only_silent', cmd_read_only_silent)

    add_cmd_helloworld()
    add_cmd_filegui()
    add_silent_commands()
