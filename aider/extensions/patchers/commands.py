from aider.commands import Commands

def apply_patch():
    def add_cmd_helloworld():
        def cmd_helloworld(self, args):
            "Output Hello"
            self.io.tool_output("Hello")

        setattr(Commands, 'cmd_helloworld', cmd_helloworld)

    add_cmd_helloworld()
