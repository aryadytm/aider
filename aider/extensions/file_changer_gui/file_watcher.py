import os
import sys
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

AIDER_FILES_FILE = ".aider-files.json"


class AiderFileHandler(FileSystemEventHandler):
    def __init__(self, coder):
        self.coder = coder
        self.sync_files_from_aider_files_json()

    def on_modified(self, event):
        if event.src_path.endswith(AIDER_FILES_FILE):  # type: ignore
            self.sync_files_from_aider_files_json()

    def sync_files_from_aider_files_json(self):
        aider_files_json = os.path.join(self.coder.root, AIDER_FILES_FILE)
        if os.path.exists(aider_files_json):
            existing_files = set(self.coder.get_inchat_relative_files())
            existing_read_only_files = set(
                self.coder.get_rel_fname(fname)
                for fname in self.coder.abs_read_only_fnames
            )

            with open(aider_files_json, "r") as f:
                file_list = json.load(f)

            new_files = set()
            new_read_only_files = set()
            for file_obj in file_list:
                file = file_obj["filename"]
                is_read_only = file_obj.get("is_read_only", False)
                abs_path = (
                    file
                    if os.path.isabs(file)
                    else os.path.abspath(os.path.join(self.coder.root, file))
                )
                rel_path = os.path.relpath(abs_path, self.coder.root)
                if os.path.exists(abs_path):
                    if is_read_only:
                        new_read_only_files.add(rel_path)
                    else:
                        new_files.add(rel_path)
                else:
                    self.coder.io.tool_error(
                        f"File does not exist and will not be added: {abs_path}"
                    )

            files_to_remove = existing_files - new_files
            read_only_files_to_remove = existing_read_only_files - new_read_only_files
            files_to_add = new_files - existing_files
            read_only_files_to_add = new_read_only_files - existing_read_only_files

            for file in files_to_remove:
                self.coder.run_one(f"/drop {file}", preproc=True)

            for file in read_only_files_to_remove:
                self.coder.run_one(f"/drop {file}", preproc=True)

            for file in files_to_add:
                self.coder.run_one(f"/add {file}", preproc=True)

            for file in read_only_files_to_add:
                self.coder.run_one(f"/read-only {file}", preproc=True)

            if (
                files_to_remove
                or read_only_files_to_remove
                or files_to_add
                or read_only_files_to_add
            ):
                pass

            self.coder.first_launch = False


class FileWatcherExtension:
    def __init__(self, coder):
        self.coder = coder
        self.file_observer = None

    def setup(self):
        print("\033[92m")  # ANSI escape code for green text
        print(
            "+----------------------------------------------------------------------+"
        )
        print(
            "| YOU ARE USING SPECIAL VERSION OF AIDER THAT READS `.aider-files.json` |"
        )
        print(
            "+----------------------------------------------------------------------+"
        )
        print("\033[0m")  # ANSI escape code to reset text color
        print("Coder Root:", self.coder.root)
        aider_files_json = os.path.join(self.coder.root, AIDER_FILES_FILE)
        event_handler = AiderFileHandler(self.coder)
        self.file_observer = Observer()
        self.file_observer.schedule(
            event_handler, os.path.dirname(aider_files_json), recursive=False
        )
        self.file_observer.start()

    def cleanup(self):
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()


def apply_patch():
    pass


def setup_extension(coder):
    extension = FileWatcherExtension(coder)
    extension.setup()
    return extension
