import os
import sys
import json
import signal
import argparse
from pathlib import Path
from typing import List, Optional
from os import path
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QTreeView,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QLabel,
    QMainWindow,
    QAction,
    QMessageBox,
    QShortcut,
    QMenu,
    QCheckBox,
    QSplitter,
)
from PyQt5.QtGui import (
    QStandardItemModel,
    QStandardItem,
    QKeySequence,
    QFont,
    QCursor,
    QClipboard,
)
from PyQt5.QtCore import Qt, QModelIndex, QSize, QTimer, QSortFilterProxyModel
from pathlib import Path


DEFAULT_DIRECTORY = os.getcwd()
DEFAULT_FORMATS = "py,js,jsx,ts,tsx,swift,java,c,cs,cpp,md,mdx,kt,ktx,json,yaml,yml,env,txt,sh,scm"
DEFAULT_FORMATS = ','.join(fmt for fmt in DEFAULT_FORMATS.split(',') if fmt.strip())
AIDER_FILES_NAME = ".aider-files.json"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Aider File Selector")
    parser.add_argument(
        "-d", "--directory", type=str, help="Specify the working directory"
    )
    return parser.parse_args()


class AiderFileGUIApp(QMainWindow):
    def __init__(self, working_directory=None):
        super().__init__()
        self.current_preset = None
        self.aider_files_path: Optional[str] = None
        self.working_directory = working_directory or DEFAULT_DIRECTORY
        self.initUI()
        self.apply_dark_theme()

    def initUI(self) -> None:
        self.setWindowIconText("Aider File Selector")
        self.setWindowTitle("Aider File Selector")
        self.setGeometry(300, 300, 300, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.readonly_files = set()

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.working_directory)
        dir_layout.addWidget(self.dir_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        browse_btn.setProperty("class", "button")
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)

        # File formats
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("File formats:"))
        self.format_input = QLineEdit(DEFAULT_FORMATS)
        format_layout.addWidget(self.format_input)
        layout.addLayout(format_layout)

        # Refresh Files button
        refresh_btn = QPushButton("Refresh Files")
        refresh_btn.clicked.connect(self.scan_directory)
        refresh_btn.setProperty("class", "button")
        layout.addWidget(refresh_btn)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_bar)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        self.clear_button.setProperty("class", "button")
        search_layout.addWidget(self.clear_button)

        layout.addLayout(search_layout)

        # Tree view
        self.model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree_view)

        # Create a QSplitter
        splitter = QSplitter(Qt.Vertical)
        
        # Add the main tree view to the splitter
        splitter.addWidget(self.tree_view)
        
        # Create a widget for the read-only section
        readonly_widget = QWidget()
        readonly_layout = QVBoxLayout(readonly_widget)
        readonly_layout.addWidget(QLabel("Read-only Files:"))
        
        self.readonly_model = QStandardItemModel()
        self.readonly_proxy_model = QSortFilterProxyModel()
        self.readonly_proxy_model.setSourceModel(self.readonly_model)
        self.readonly_proxy_model.setRecursiveFilteringEnabled(True)
        self.readonly_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.readonly_tree_view = QTreeView()
        self.readonly_tree_view.setModel(self.readonly_proxy_model)
        self.readonly_tree_view.setHeaderHidden(True)
        self.readonly_tree_view.setAlternatingRowColors(True)
        self.readonly_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.readonly_tree_view.customContextMenuRequested.connect(self.show_readonly_context_menu)
        readonly_layout.addWidget(self.readonly_tree_view)
        
        # Add the read-only widget to the splitter
        splitter.addWidget(readonly_widget)
        
        # Set the sizes of the splitter to make the read-only section smaller
        splitter.setSizes([800, 400])  # Adjust these values as needed
        
        # Add the splitter to the main layout
        layout.addWidget(splitter)

        # Search delay timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Select All button
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        select_all_btn.setProperty("class", "button")
        buttons_layout.addWidget(select_all_btn)

        # Unselect All button
        unselect_all_btn = QPushButton("Unselect All")
        unselect_all_btn.clicked.connect(self.unselect_all)
        unselect_all_btn.setProperty("class", "button")
        buttons_layout.addWidget(unselect_all_btn)

        # Print button
        print_btn = QPushButton("Print Selected Files")
        print_btn.clicked.connect(self.print_selected_files)
        print_btn.setProperty("class", "button")
        buttons_layout.addWidget(print_btn)

        layout.addLayout(buttons_layout)

        # Copy to Clipboard button
        copy_clipboard_btn = QPushButton("Copy to Clipboard")
        copy_clipboard_btn.clicked.connect(self.copy_selected_files_to_clipboard)
        copy_clipboard_btn.setProperty("class", "button")
        layout.addWidget(copy_clipboard_btn)

        # Connect the itemChanged signal to our new method
        self.model.itemChanged.connect(self.on_item_changed)

        # Create menu bar
        self.create_menu_bar()

        # Add shortcut for Save action
        self.create_shortcuts()

        self.scan_directory()

        # Set font
        font = QFont("Segoe UI", 10)
        self.setFont(font)

    def apply_dark_theme(self):
        # Apply QSS styling
        chevron_right_path = os.path.join(os.path.dirname(__file__), 'images/chevron-right.png').replace("\\", "/")
        chevron_down_path = os.path.join(os.path.dirname(__file__), 'images/chevron-down.png').replace("\\", "/")
        
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background-color: #353535;
                color: #ffffff;
            }}
            QLineEdit, QTreeView {{
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: #4a4a4a;
                color: #ffffff;
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #5a5a5a;
            }}
            QTreeView {{
                alternate-background-color: #323232;
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url({chevron_right_path});
                background-color: transparent;
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url({chevron_down_path});
                background-color: transparent;
            }}
            QTreeView::branch:has-children:!has-siblings:closed:hover,
            QTreeView::branch:closed:has-children:has-siblings:hover,
            QTreeView::branch:open:has-children:!has-siblings:hover,
            QTreeView::branch:open:has-children:has-siblings:hover {{
                background-color: #6b6b6b55;
            }}
            QMenuBar {{
                background-color: #2b2b2b;
                color: #ffffff;
            }}
            QMenuBar::item:selected {{
                background-color: #5a5a5a;
            }}
            QMenu::item:selected {{
                background-color: #7b7b7b;
            }}
        """
        )

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        load_preset_action = QAction("Open...", self)
        load_preset_action.triggered.connect(self.load_preset)
        file_menu.addAction(load_preset_action)

        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save_preset)
        file_menu.addAction(self.save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.save_preset_as)
        file_menu.addAction(save_as_action)

    def create_shortcuts(self):
        # Create a shortcut for the Save action
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_preset)

        # Create a shortcut for closing the application
        close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        close_shortcut.activated.connect(self.close_application)

    def browse_directory(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.dir_input.setText(dir_path)

    def scan_directory(self) -> None:
        checkbox_states = self.store_checkbox_states()
        expansion_states = self.store_expansion_states()

        directory = Path(self.dir_input.text())
        self.current_expansion_states = expansion_states  # Store expansion states
        self.aider_files_path = str(directory / AIDER_FILES_NAME)
        formats = [f.strip() for f in self.format_input.text().split(",") if f.strip()]
        formats = [fmt for fmt in formats if fmt != ""]  # Ensure empty string is not included
        if not formats:
            formats = ["txt"]  # Default to txt if no valid formats are provided
        self.model.clear()
        root = self.model.invisibleRootItem()
        self.populate_tree(root, directory, formats)

        # Read the JSON file and update the checkboxes and readonly files
        if os.path.exists(self.aider_files_path):
            with open(self.aider_files_path, 'r') as f:
                data = json.load(f)
            
            for item in data:
                filename = item['filename']
                is_read_only = item.get('is_read_only', False)
                
                if filename == '*':
                    self.select_all()
                elif is_read_only:
                    self.readonly_files.add(os.path.join(directory, filename))
                else:
                    self.set_item_checked(filename, True)

        self.restore_checkbox_states(checkbox_states)
        if hasattr(self, 'current_expansion_states'):
            self.restore_expansion_states(self.current_expansion_states)
        self.update_aider_files_json()
        
        # Populate the read-only files tree
        self.populate_readonly_tree(directory)

    def populate_tree(
        self, parent: QStandardItem, path: Path, formats: List[str]
    ) -> None:
        folders = []
        files = []

        try:
            for item in path.iterdir():
                if item.is_dir():
                    if self.is_valid_directory(item) and not self.is_empty_folder(item):
                        folders.append(item)
                elif self.is_valid_file(item):
                    files.append(item)
        except PermissionError:
            print(f"Permission denied: {path}")
            return

        folders.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())

        for item in folders:
            folder_item = self.add_item(parent, item.name, item)
            self.populate_tree(folder_item, item, formats)

        for item in files:
            self.add_item(parent, item.name, item)

        if not files and not folders:
            print(f"Warning: No valid files or non-empty folders found in {path}")

    def add_item(self, parent: QStandardItem, name: str, path: Path) -> QStandardItem:
        item = QStandardItem(name)
        item.setCheckable(True)
        item.setData(str(path), Qt.UserRole)
        if path.is_dir():
            item.setData("folder", Qt.UserRole + 1)
        parent.appendRow(item)
        return item

    def print_selected_files(self) -> None:
        selected_files = self.get_checked_files(self.model.invisibleRootItem())
        for file in selected_files:
            print(file)

    def get_checked_files(self, parent: QStandardItem) -> List[Path]:
        checked_files = []
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item.checkState() == Qt.Checked:
                path = Path(item.data(Qt.UserRole))
                if item.data(Qt.UserRole + 1) == "folder":
                    checked_files.extend(self.get_all_files_in_folder(path))
                else:
                    checked_files.append(path)
            elif item.hasChildren() and item.checkState() == Qt.PartiallyChecked:
                checked_files.extend(self.get_checked_files(item))
        return checked_files

    def get_all_files_in_folder(self, folder_path: Path) -> List[Path]:
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if self.is_valid_directory(Path(os.path.join(root, d)))]
            for file in files:
                file_path = Path(os.path.join(root, file))
                if self.is_valid_file(file_path):
                    all_files.append(file_path)
        return all_files

    def is_valid_file(self, file_path: Path) -> bool:
        """
        Check if a file is valid for inclusion in the file tree.
        A file is considered valid if it has an extension, matches the specified formats,
        and is not a .DS_Store file.
        
        :param file_path: Path object representing the file
        :return: True if the file is valid, False otherwise
        """
        if file_path.name == '.DS_Store':
            return False
        _, extension = os.path.splitext(file_path)
        return extension != '' and any(file_path.name.endswith(f".{fmt}") for fmt in self.format_input.text().split(","))

    def is_valid_directory(self, dir_path: Path) -> bool:
        """
        Check if a directory should be included in the file tree.
        Excludes __pycache__ directories.
        
        :param dir_path: Path object representing the directory
        :return: True if the directory is valid, False otherwise
        """
        return dir_path.name != '__pycache__'

    def is_empty_folder(self, folder_path: Path) -> bool:
        """
        Check if a folder is empty, excluding hidden files and __pycache__.
        
        :param folder_path: Path object representing the folder
        :return: True if the folder is empty, False otherwise
        """
        for item in folder_path.iterdir():
            if not item.name.startswith('.') and item.name != '__pycache__':
                return False
        return True

    def save_preset(self):
        if self.current_preset:
            self.save_preset_to_file(self.current_preset)
        else:
            self.save_preset_as()

    def save_preset_as(self):
        documents_dir = os.path.expanduser("~/Documents")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", documents_dir, "JSON Files (*.json)"
        )
        if filename:
            self.save_preset_to_file(filename)
            self.current_preset = filename

    def save_preset_to_file(self, filename):
        preset_data = {
            "directory": self.dir_input.text(),
            "formats": self.format_input.text(),
            "checkbox_states": self.store_checkbox_states(),
            "expansion_states": self.store_expansion_states(),
        }
        with open(filename, "w") as f:
            json.dump(preset_data, f)
        QMessageBox.information(self, "Success", f"Preset saved to {filename}")

    def load_preset(self):
        documents_dir = os.path.expanduser("~/Documents")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", documents_dir, "JSON Files (*.json)"
        )
        if filename:
            with open(filename, "r") as f:
                preset_data = json.load(f)

            self.dir_input.setText(preset_data["directory"])
            self.format_input.setText(preset_data["formats"])

            self.scan_directory()

            self.restore_checkbox_states(preset_data["checkbox_states"])
            self.restore_expansion_states(preset_data["expansion_states"])

            self.current_preset = filename
            QMessageBox.information(self, "Success", f"Preset loaded from {filename}")

    def set_item_checked(self, filename: str, checked: bool):
        item = self.find_item_by_filename(self.model.invisibleRootItem(), filename)
        if item:
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def find_item_by_filename(
        self, parent: QStandardItem, filename: str
    ) -> Optional[QStandardItem]:
        for row in range(parent.rowCount()):
            item = parent.child(row)
            item_path = self.get_relative_path(Path(item.data(Qt.UserRole)))
            if item_path == filename:
                return item
            if item.hasChildren():
                found_item = self.find_item_by_filename(item, filename)
                if found_item:
                    return found_item
        return None
    
    def store_checkbox_states(self) -> dict:
        states = {}
        self.store_checkbox_states_recursive(self.model.invisibleRootItem(), states)
        return states

    def store_checkbox_states_recursive(
        self, parent: QStandardItem, states: dict
    ) -> None:
        for row in range(parent.rowCount()):
            item = parent.child(row)
            path = item.data(Qt.UserRole)
            states[path] = item.checkState()
            if item.hasChildren():
                self.store_checkbox_states_recursive(item, states)

    def restore_checkbox_states(self, states: dict) -> None:
        self.restore_checkbox_states_recursive(self.model.invisibleRootItem(), states)

    def restore_checkbox_states_recursive(
        self, parent: QStandardItem, states: dict
    ) -> None:
        for row in range(parent.rowCount()):
            item = parent.child(row)
            path = item.data(Qt.UserRole)
            if path in states:
                item.setCheckState(states[path])
            if item.hasChildren():
                self.restore_checkbox_states_recursive(item, states)

    def store_expansion_states(self) -> dict:
        states = {}
        self.store_expansion_states_recursive(
            self.model.invisibleRootItem(), self.tree_view.rootIndex(), states, ""
        )
        return states

    def store_expansion_states_recursive(
        self, parent: QStandardItem, parent_index: QModelIndex, states: dict, current_path: str
    ) -> None:
        for row in range(parent.rowCount()):
            child_index = self.model.index(row, 0, parent_index)
            item = self.model.itemFromIndex(child_index)
            path = os.path.join(current_path, item.text())
            states[path] = self.tree_view.isExpanded(child_index)
            if item.hasChildren():
                self.store_expansion_states_recursive(item, child_index, states, path)

    def restore_expansion_states(self, states: dict) -> None:
        self.restore_expansion_states_recursive(
            self.model.invisibleRootItem(), self.tree_view.rootIndex(), states, ""
        )

    def restore_expansion_states_recursive(
        self, parent: QStandardItem, parent_index: QModelIndex, states: dict, current_path: str
    ) -> None:
        for row in range(parent.rowCount()):
            child_index = self.model.index(row, 0, parent_index)
            item = self.model.itemFromIndex(child_index)
            path = os.path.join(current_path, item.text())
            if path in states:
                self.tree_view.setExpanded(child_index, states[path])
            if item.hasChildren():
                self.restore_expansion_states_recursive(item, child_index, states, path)

    def on_item_changed(self, item: QStandardItem) -> None:
        # Disconnect the signal temporarily to avoid recursive calls
        self.model.itemChanged.disconnect(self.on_item_changed)

        if item.isCheckable():
            check_state = item.checkState()
            self.check_children(item, check_state)
            self.check_parents(item.parent())

            # If it's a folder, update its children
            if item.data(Qt.UserRole + 1) == "folder":
                self.update_folder_children(item, check_state)

        # Reconnect the signal
        self.model.itemChanged.connect(self.on_item_changed)

        # Update .aider-files.json
        self.update_aider_files_json()

    def update_folder_children(self, folder_item: QStandardItem, check_state: Qt.CheckState):
        for row in range(folder_item.rowCount()):
            child = folder_item.child(row)
            child.setCheckState(check_state)
            if child.data(Qt.UserRole + 1) == "folder":
                self.update_folder_children(child, check_state)

    def check_children(self, item: QStandardItem, check_state: Qt.CheckState) -> None:
        for row in range(item.rowCount()):
            child = item.child(row)
            child.setCheckState(check_state)
            if child.hasChildren():
                self.check_children(child, check_state)

    def check_parents(self, parent: QStandardItem) -> None:
        if parent is None:
            return

        checked_count = 0
        unchecked_count = 0
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.checkState() == Qt.Checked:
                checked_count += 1
            elif child.checkState() == Qt.Unchecked:
                unchecked_count += 1

        if checked_count == parent.rowCount():
            parent.setCheckState(Qt.Checked)
        elif unchecked_count == parent.rowCount():
            parent.setCheckState(Qt.Unchecked)
        else:
            parent.setCheckState(Qt.PartiallyChecked)

        self.check_parents(parent.parent())

    def get_relative_path(self, abs_path: Path) -> str:
        try:
            return os.path.relpath(abs_path, self.dir_input.text())
        except ValueError:
            # This can happen on Windows if the paths are on different drives
            return str(abs_path)

    def update_aider_files_json(self) -> None:
        if self.aider_files_path is None:
            return

        checked_files = self.get_checked_files(self.model.invisibleRootItem())
        readonly_files = self.get_checked_readonly_files()
        try:
            data = []
            if not checked_files and not readonly_files:
                data = []
            elif len(checked_files) == self.count_all_files(self.model.invisibleRootItem()):
                data = [{"filename": "*", "is_read_only": False}]
            else:
                for file in checked_files:
                    if self.is_valid_file(file):
                        rel_path = self.get_relative_path(file)
                        data.append({"filename": rel_path, "is_read_only": False})
                for file in readonly_files:
                    file_path = Path(file)
                    if self.is_valid_file(file_path):
                        rel_path = self.get_relative_path(file_path)
                        data.append({"filename": rel_path, "is_read_only": True})

            with open(self.aider_files_path, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            QMessageBox.warning(
                self, "Error", f"Failed to update {AIDER_FILES_NAME}: {str(e)}"
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"An unexpected error occurred: {str(e)}"
            )

    def get_checked_readonly_files(self):
        checked_files = []
        root = self.readonly_model.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            self.get_checked_readonly_files_recursive(item, checked_files)
        return checked_files

    def get_checked_readonly_files_recursive(self, item, checked_files):
        if item.isCheckable() and item.checkState() == Qt.Checked:
            file_path = item.data(Qt.UserRole)
            if file_path:
                checked_files.append(file_path)
        for row in range(item.rowCount()):
            child = item.child(row)
            self.get_checked_readonly_files_recursive(child, checked_files)

    def populate_readonly_tree(self, directory: Path) -> None:
        self.readonly_model.clear()
        root = self.readonly_model.invisibleRootItem()
        for file_path in self.readonly_files:
            relative_path = self.get_relative_path(Path(file_path))
            path_parts = relative_path.split(os.path.sep)
            current_item = root
            for i, part in enumerate(path_parts):
                child = self.find_child(current_item, part)
                if child is None:
                    child = QStandardItem(part)
                    child.setEditable(False)
                    child.setCheckable(True)
                    child.setCheckState(Qt.Checked)
                    current_item.appendRow(child)
                if i == len(path_parts) - 1:  # If it's a file
                    child.setData(file_path, Qt.UserRole)  # Store the full path as data
                current_item = child
        
        # Connect the itemChanged signal to handle checkbox changes
        self.readonly_model.itemChanged.connect(self.on_readonly_item_changed)

    def find_child(self, parent: QStandardItem, text: str) -> Optional[QStandardItem]:
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.text() == text:
                return child
        return None

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if index.isValid():
            item = self.model.itemFromIndex(self.proxy_model.mapToSource(index))
            file_path = item.data(Qt.UserRole)
            
            menu = QMenu(self)
            if item.hasChildren():
                add_folder_action = menu.addAction("Add folder to Read-only")
                add_folder_action.triggered.connect(lambda: self.add_folder_to_readonly(file_path))
            else:
                add_action = menu.addAction("Add to Read-only")
                add_action.triggered.connect(lambda: self.add_to_readonly(file_path))
            
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def show_readonly_context_menu(self, position):
        index = self.readonly_tree_view.indexAt(position)
        if index.isValid():
            item = self.readonly_model.itemFromIndex(self.readonly_proxy_model.mapToSource(index))
            file_path = item.data(Qt.UserRole)
            
            menu = QMenu(self)
            if item.hasChildren():
                remove_action = menu.addAction("Remove folder from Read-only")
                remove_action.triggered.connect(lambda: self.remove_folder_from_readonly(item))
            else:
                remove_action = menu.addAction("Remove from Read-only")
                remove_action.triggered.connect(lambda: self.remove_from_readonly(file_path))
            
            menu.exec_(self.readonly_tree_view.viewport().mapToGlobal(position))

    def remove_folder_from_readonly(self, folder_item):
        folder_path = folder_item.data(Qt.UserRole)
        if folder_path:
            self.remove_from_readonly(folder_path)
        else:
            # If the folder_path is None, it means we're dealing with a virtual folder
            # In this case, we need to remove all child items
            self.remove_children_from_readonly(folder_item)
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.update_aider_files_json()

    def remove_children_from_readonly(self, parent_item):
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row)
            file_path = child.data(Qt.UserRole)
            if file_path:
                self.readonly_files.discard(file_path)
            else:
                self.remove_children_from_readonly(child)

    def add_to_readonly(self, file_path):
        if file_path not in self.readonly_files:
            self.readonly_files.add(file_path)
            self.populate_readonly_tree(Path(self.dir_input.text()))
            self.update_aider_files_json()

    def add_folder_to_readonly(self, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in self.readonly_files:
                    self.readonly_files.add(file_path)
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.update_aider_files_json()

    def remove_from_readonly(self, file_path):
        if file_path is None:
            return
        
        if os.path.isdir(file_path):
            # Remove all files that start with this directory path
            self.readonly_files = {f for f in self.readonly_files if not f.startswith(file_path)}
        else:
            # Remove the specific file if it exists in readonly_files
            self.readonly_files.discard(file_path)
        
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.update_aider_files_json()

    def on_readonly_item_changed(self, item):
        if item.isCheckable():
            file_path = item.data(Qt.UserRole)
            if file_path:  # This is a file
                if item.checkState() == Qt.Checked:
                    self.readonly_files.add(file_path)
                else:
                    self.readonly_files.discard(file_path)
            else:  # This is a folder
                self.update_readonly_folder_children(item, item.checkState())
            
            # Update all parents
            self.update_parent_check_state(item.parent())
            
            self.update_aider_files_json()

    def update_readonly_folder_children(self, folder_item, check_state):
        if check_state != Qt.PartiallyChecked:
            for row in range(folder_item.rowCount()):
                child = folder_item.child(row)
                child.setCheckState(check_state)
                file_path = child.data(Qt.UserRole)
                if file_path:  # This is a file
                    if check_state == Qt.Checked:
                        self.readonly_files.add(file_path)
                    else:
                        self.readonly_files.discard(file_path)
                else:  # This is a subfolder
                    self.update_readonly_folder_children(child, check_state)

    def update_parent_check_state(self, parent):
        if parent is None or parent == self.readonly_model.invisibleRootItem():
            return

        children_states = [parent.child(i).checkState() for i in range(parent.rowCount())]
        if all(state == Qt.Checked for state in children_states):
            parent.setCheckState(Qt.Checked)
        elif all(state == Qt.Unchecked for state in children_states):
            parent.setCheckState(Qt.Unchecked)
        else:
            parent.setCheckState(Qt.PartiallyChecked)

        self.update_parent_check_state(parent.parent())

    def count_all_files(self, parent: QStandardItem) -> int:
        count = 0
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item.hasChildren():
                count += self.count_all_files(item)
            else:
                count += 1
        return count

    def on_search_text_changed(self, text):
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay

    def apply_filter(self):
        search_text = self.search_bar.text()
        self.proxy_model.setFilterRegExp(search_text)

    def clear_search(self):
        self.search_bar.clear()
        self.proxy_model.setFilterRegExp("")

    def close_application(self):
        sys.exit(0)

    def select_all(self):
        self.set_check_state_recursive(self.model.invisibleRootItem(), Qt.Checked)
        self.update_aider_files_json()

    def unselect_all(self):
        self.set_check_state_recursive(self.model.invisibleRootItem(), Qt.Unchecked)
        self.update_aider_files_json()

    def set_check_state_recursive(self, parent: QStandardItem, state: Qt.CheckState):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            item.setCheckState(state)
            if item.hasChildren():
                self.set_check_state_recursive(item, state)

    def copy_selected_files_to_clipboard(self):
        fence = "`" * 3
        selected_files = self.get_checked_files(self.model.invisibleRootItem())
        selected_files += self.get_checked_readonly_files()
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one file to copy.")
            return
        
        formatted_content = ""
        for file_path in selected_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    file_format = str(file_path).split('.')[-1]
                    formatted_content += f"{file_path}\n{fence}{file_format}\n{content}\n{fence}\n\n"
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error reading file {file_path}: {str(e)}")
                return
        
        clipboard = QApplication.clipboard()
        try:
            clipboard.setText(formatted_content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error copying to clipboard: {str(e)}")

def signal_handler(signum, frame):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    args = parse_arguments()

    if args.directory:
        working_directory = args.directory
    else:
        working_directory = DEFAULT_DIRECTORY

    app = QApplication(sys.argv)
    ex = AiderFileGUIApp(working_directory)
    ex.show()
    sys.exit(app.exec_())
