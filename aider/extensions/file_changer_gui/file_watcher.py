import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

AIDER_FILES_FILE = '.aider-files.txt'


class AiderFileHandler(FileSystemEventHandler):
    def __init__(self, coder):
        self.coder = coder
        self.sync_files_from_aider_files_txt()

    def on_modified(self, event):
        if event.src_path.endswith(AIDER_FILES_FILE):
            self.sync_files_from_aider_files_txt()
        
    def sync_files_from_aider_files_txt(self):
        aider_files_txt = os.path.join(self.coder.root, AIDER_FILES_FILE)
        if os.path.exists(aider_files_txt):
            existing_files = set(self.coder.get_inchat_relative_files())

            with open(aider_files_txt, "r") as f:
                file_list = [line.strip() for line in f if line.strip()]

            abs_file_list = set()
            for file in file_list:
                abs_path = (
                    file
                    if os.path.isabs(file)
                    else os.path.abspath(os.path.join(self.coder.root, file))
                )
                if os.path.exists(abs_path):
                    abs_file_list.add(abs_path)
                else:
                    self.coder.io.tool_error(
                        f"File does not exist and will not be added: {abs_path}"
                    )

            new_files = {os.path.relpath(f, self.coder.root) for f in abs_file_list - set(map(self.coder.abs_root_path, existing_files)) if os.path.exists(f)}
            removed_files = {f for f in existing_files if self.coder.abs_root_path(f) not in abs_file_list}

            for removed_file in removed_files:
                self.coder.run_one(f"/drop {removed_file}", preproc=True)

            for new_file in new_files:
                self.coder.run_one(f"/add {new_file}", preproc=True)

            if new_files or removed_files:
                pass

            self.coder.first_launch = False


class FileWatcherExtension:
    def __init__(self, coder):
        self.coder = coder
        self.file_observer = None

    def setup(self):
        print("\033[92m")  # ANSI escape code for green text
        print("+----------------------------------------------------------------------+")
        print("| YOU ARE USING SPECIAL VERSION OF AIDER THAT READS `.aider-files.txt` |")
        print("+----------------------------------------------------------------------+")
        print("\033[0m")  # ANSI escape code to reset text color
        print("Coder Root:", self.coder.root)
        aider_files_txt = os.path.join(self.coder.root, AIDER_FILES_FILE)
        event_handler = AiderFileHandler(self.coder)
        self.file_observer = Observer()
        self.file_observer.schedule(event_handler, os.path.dirname(aider_files_txt), recursive=False)
        self.file_observer.start()

    def cleanup(self):
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()

def setup_extension(coder):
    extension = FileWatcherExtension(coder)
    extension.setup()
    return extension