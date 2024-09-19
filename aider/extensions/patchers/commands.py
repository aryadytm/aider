from aider.commands import Commands
from PyQt5.QtWidgets import QApplication
from aider.extensions.file_changer_gui.start_gui import AiderFileGUIApp
import sys

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
                from PyQt5.QtWidgets import QApplication
            except ImportError:
                self.io.tool_error("PyQt5 is not installed. Please install it to use the file GUI.")
                return

            self.io.tool_output("Starting the file GUI...")
            app = QApplication([])
            ex = AiderFileGUIApp(self.coder.root)
            ex.show()
            sys.exit(app.exec_())

        setattr(Commands, 'cmd_filegui', cmd_filegui)

    add_cmd_helloworld()
    add_cmd_filegui()
