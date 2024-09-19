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

    add_cmd_helloworld()
    add_cmd_filegui()
