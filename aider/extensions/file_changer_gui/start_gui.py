import os
import sys
import json
import signal
import argparse
import traceback  # Import traceback for detailed error information
from pathlib import Path
from typing import List, Optional, Dict, Set

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTreeView,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QLabel,
    QAction,
    QMessageBox,
    QShortcut,
    QMenu,
    QSplitter,
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeySequence, QFont
from PyQt5.QtCore import Qt, QModelIndex, QTimer, QSortFilterProxyModel

DEFAULT_DIRECTORY = os.getcwd()
DEFAULT_FORMATS = "py,js,jsx,ts,tsx,swift,java,c,cs,cpp,md,mdx,kt,ktx,json,yaml,yml,env,txt,sh,scm,prisma"
PATH_AIDER_FILES_JSON = ".aider-files.json"
PATH_PRESET_JSON = ".aider-filegui-preset.json"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Aider File Selector")
    parser.add_argument(
        "-d", "--directory", type=str, help="Specify the working directory"
    )
    return parser.parse_args()


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler that prints the full traceback and shows a message box.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow keyboard interrupts to exit gracefully
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Print the traceback to stderr
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    # Show a message box with the error details
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    # Ensure that a QApplication instance exists
    if QApplication.instance() is not None:
        QMessageBox.critical(None, "An Uncaught Error Occurred", error_msg)
    else:
        print("Fatal Error: ", error_msg)


class AiderFileGUIApp(QMainWindow):
    def __init__(self, working_directory=None):
        super().__init__()
        self.working_directory = working_directory or DEFAULT_DIRECTORY
        self.aider_files_path: Optional[str] = None
        self.readonly_files: Set[str] = set()  # Stores checked read-only files
        self.readonly_tree_files: Set[str] = (
            set()
        )  # Stores all files in the read-only tree
        self.current_preset: Optional[str] = None
        self.preset_expansion_states: Dict[str, bool] = {}
        self.preset_readonly_expansion_states: Dict[str, bool] = {}  # Added

        self.preset_file_path = os.path.join(self.working_directory, PATH_PRESET_JSON)

        self.init_ui()
        self.apply_dark_theme()
        self.load_preset()
        self.scan_directory()

    def init_ui(self):
        self.setWindowTitle("Aider File Selector")
        self.setGeometry(300, 300, 300, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.setup_directory_selection(main_layout)
        self.setup_file_formats_input(main_layout)
        self.setup_search_bar(main_layout)
        self.setup_tree_views(main_layout)
        self.setup_buttons(main_layout)
        self.create_shortcuts()

        font = QFont("Segoe UI", 10)
        self.setFont(font)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

    def setup_directory_selection(self, layout):
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.working_directory)
        dir_layout.addWidget(self.dir_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(
            lambda: self.scan_directory(maintain_expansion=True)
        )
        dir_layout.addWidget(refresh_btn)
        layout.addLayout(dir_layout)

    def setup_file_formats_input(self, layout):
        format_layout = QHBoxLayout()
        # Removed the "File formats:" label
        self.format_input = QLineEdit(DEFAULT_FORMATS)
        format_layout.addWidget(self.format_input)
        self.format_input.textChanged.connect(self.on_format_input_changed)
        layout.addLayout(format_layout)

    def setup_expand_collapse_buttons(self, layout):
        """
        Adds 'Expand All' and 'Collapse All' buttons below the directory selection.
        """
        expand_collapse_layout = QHBoxLayout()

        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.expand_all)
        expand_collapse_layout.addWidget(expand_all_btn)

        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.collapse_all)
        expand_collapse_layout.addWidget(collapse_all_btn)

        layout.addLayout(expand_collapse_layout)

    def expand_all(self):
        """
        Expands all nodes in both the main and read-only tree views.
        """
        self.tree_view.expandAll()
        self.readonly_tree_view.expandAll()

    def collapse_all(self):
        """
        Collapses all nodes in both the main and read-only tree views.
        """
        self.tree_view.collapseAll()
        self.readonly_tree_view.collapseAll()

    def setup_search_bar(self, layout):
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search files...")
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_bar)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_button)
        layout.addLayout(search_layout)

    def setup_tree_views(self, layout):
        splitter = QSplitter(Qt.Vertical)

        # Main Tree View
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
        self.tree_view.expanded.connect(self.on_tree_expanded)
        self.tree_view.collapsed.connect(self.on_tree_collapsed)
        splitter.addWidget(self.tree_view)

        # Read-only Tree View
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
        self.readonly_tree_view.customContextMenuRequested.connect(
            self.show_readonly_context_menu
        )
        self.readonly_tree_view.expanded.connect(self.on_readonly_tree_expanded)
        self.readonly_tree_view.collapsed.connect(self.on_readonly_tree_collapsed)
        splitter.addWidget(self.readonly_tree_view)

        splitter.setSizes([3000, 1000])  # Adjusted to distribute space (Requirement 2)
        layout.addWidget(splitter)

    def setup_buttons(self, layout):
        buttons_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        buttons_layout.addWidget(select_all_btn)

        unselect_all_btn = QPushButton("Unselect All")
        unselect_all_btn.clicked.connect(self.unselect_all)
        buttons_layout.addWidget(unselect_all_btn)

        # Removed the "Print Selected Files" button
        layout.addLayout(buttons_layout)
        self.setup_expand_collapse_buttons(layout)

        copy_clipboard_btn = QPushButton("Copy to Clipboard")
        copy_clipboard_btn.clicked.connect(self.copy_selected_files_to_clipboard)
        layout.addWidget(copy_clipboard_btn)

    def create_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_preset)

        close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        close_shortcut.activated.connect(self.close_application)

    def apply_dark_theme(self):
        chevron_right_path = os.path.join(
            os.path.dirname(__file__), "images/chevron-right.png"
        ).replace("\\", "/")
        chevron_down_path = os.path.join(
            os.path.dirname(__file__), "images/chevron-down.png"
        ).replace("\\", "/")

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

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.dir_input.setText(dir_path)
            self.scan_directory()

    def scan_directory(self, maintain_expansion=False):
        directory = Path(self.dir_input.text())
        self.aider_files_path = str(directory / PATH_AIDER_FILES_JSON)
        formats = [f.strip() for f in self.format_input.text().split(",") if f.strip()]
        formats = formats if formats else ["txt"]

        checkbox_states = self.store_checkbox_states()
        if maintain_expansion:
            expansion_states = self.store_expansion_states()
            readonly_expansion_states = self.store_readonly_expansion_states()  # Added
        else:
            expansion_states = self.preset_expansion_states
            readonly_expansion_states = self.preset_readonly_expansion_states  # Added

        try:
            self.model.itemChanged.disconnect(self.on_item_changed)
        except TypeError:
            pass

        self.model.clear()
        self.populate_tree(self.model.invisibleRootItem(), directory, formats)
        self.restore_checkbox_states(checkbox_states)
        self.restore_expansion_states(expansion_states)

        self.model.itemChanged.connect(
            self.on_item_changed
        )  # Moved here (Requirement 1)
        self.read_aider_files_json(directory)
        self.populate_readonly_tree(directory)
        self.restore_readonly_expansion_states(readonly_expansion_states)  # Added

    def populate_tree(
        self, parent_item: QStandardItem, directory: Path, formats: List[str]
    ):
        try:
            for item in sorted(directory.iterdir(), key=lambda x: x.name.lower()):
                if item.is_dir() and self.is_valid_directory(item):
                    dir_item = self.create_tree_item(item.name, item)
                    parent_item.appendRow(dir_item)
                    self.populate_tree(dir_item, item, formats)
                elif item.is_file() and self.is_valid_file(item, formats):
                    file_item = self.create_tree_item(item.name, item)
                    parent_item.appendRow(file_item)
        except PermissionError:
            pass

    def create_tree_item(self, name: str, path: Path) -> QStandardItem:
        item = QStandardItem(name)
        item.setCheckable(True)
        item.setData(str(path), Qt.UserRole)
        item.setData("folder" if path.is_dir() else "file", Qt.UserRole + 1)
        return item

    def is_valid_file(self, file_path: Path, formats: List[str]) -> bool:
        if file_path.name == ".DS_Store":
            return False
        return file_path.suffix[1:] in formats

    def is_valid_directory(self, dir_path: Path) -> bool:
        return dir_path.name != "__pycache__" and not dir_path.name.startswith(".")

    def on_item_changed(self, item: QStandardItem):
        try:
            self.model.itemChanged.disconnect(self.on_item_changed)
            self.update_item_check_state(item)
            self.update_aider_files_json()
        except Exception as e:
            traceback.print_exc()  # Print full traceback to the console
            QMessageBox.critical(
                self, "Error", f"An unexpected error occurred: {str(e)}"
            )
        finally:
            self.model.itemChanged.connect(self.on_item_changed)

    def update_item_check_state(self, item: QStandardItem):
        check_state = item.checkState()
        self.set_children_check_state(item, check_state)
        self.update_parent_check_state(item)

    def set_children_check_state(self, item: QStandardItem, check_state: Qt.CheckState):
        for row in range(item.rowCount()):
            child = item.child(row)
            child.setCheckState(check_state)
            if child.hasChildren():
                self.set_children_check_state(child, check_state)

    def update_parent_check_state(self, item: QStandardItem):
        parent = item.parent()
        if parent is None:
            return
        checked = 0
        unchecked = 0
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.checkState() == Qt.Checked:
                checked += 1
            elif child.checkState() == Qt.Unchecked:
                unchecked += 1
        if checked == parent.rowCount():
            parent.setCheckState(Qt.Checked)
        elif unchecked == parent.rowCount():
            parent.setCheckState(Qt.Unchecked)
        else:
            parent.setCheckState(Qt.PartiallyChecked)
        self.update_parent_check_state(parent)

    def read_aider_files_json(self, directory: Path):
        aider_files = directory / PATH_AIDER_FILES_JSON
        if aider_files.exists():
            try:
                with open(aider_files, "r") as f:
                    data = json.load(f)
                for item in data.get("files", []):
                    filename = item["filename"]
                    is_read_only = item.get("is_read_only", False)
                    file_path = str(directory / filename)
                    if filename == "*":
                        self.select_all()
                    elif is_read_only:
                        self.readonly_tree_files.add(file_path)
                        self.readonly_files.add(file_path)  # Added this line
                    else:
                        self.set_item_checked(directory / filename, True)
                self.populate_readonly_tree(directory)
            except Exception as e:
                traceback.print_exc()  # Print full traceback to the console
                QMessageBox.warning(
                    self, "Error", f"Failed to read {PATH_AIDER_FILES_JSON}: {str(e)}"
                )

    def set_item_checked(self, path: Path, checked: bool):
        item = self.find_item_by_path(self.model.invisibleRootItem(), str(path))
        if item:
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.update_item_check_state(item)  # Added this line (Requirement 1)

    def find_item_by_path(
        self, parent: QStandardItem, path: str
    ) -> Optional[QStandardItem]:
        for row in range(parent.rowCount()):
            item = parent.child(row)
            item_path = item.data(Qt.UserRole)
            if item_path == path:
                return item
            if item.hasChildren():
                found_item = self.find_item_by_path(item, path)
                if found_item:
                    return found_item
        return None

    def update_aider_files_json(self):
        if self.aider_files_path is None:
            return
        data = {}
        checked_files = self.get_checked_files(self.model.invisibleRootItem())
        readonly_files = list(self.readonly_files)
        if not checked_files and not readonly_files:
            data["files"] = []
        elif len(checked_files) == self.count_all_files(self.model.invisibleRootItem()):
            data["files"] = [{"filename": "*", "is_read_only": False}]
        else:
            files_data = []
            for file_path in checked_files:
                rel_path = os.path.relpath(file_path, self.dir_input.text())
                files_data.append({"filename": rel_path, "is_read_only": False})
            for file_path in readonly_files:
                rel_path = os.path.relpath(file_path, self.dir_input.text())
                files_data.append({"filename": rel_path, "is_read_only": True})
            data["files"] = files_data
        try:
            with open(self.aider_files_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            traceback.print_exc()  # Print full traceback to the console
            QMessageBox.warning(
                self, "Error", f"Failed to update {PATH_AIDER_FILES_JSON}: {str(e)}"
            )

    def get_checked_files(self, parent: QStandardItem) -> List[str]:
        checked_files = []
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item.checkState() == Qt.Checked:
                path = item.data(Qt.UserRole)
                if item.data(Qt.UserRole + 1) == "folder":
                    checked_files.extend(self.get_all_files_in_folder(Path(path)))
                else:
                    checked_files.append(path)
            elif item.hasChildren() and item.checkState() == Qt.PartiallyChecked:
                checked_files.extend(self.get_checked_files(item))
        return checked_files

    def get_all_files_in_folder(self, folder_path: Path) -> List[str]:
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if self.is_valid_directory(Path(root) / d)]
            for file in files:
                file_path = Path(root) / file
                if self.is_valid_file(file_path, self.format_input.text().split(",")):
                    all_files.append(str(file_path))
        return all_files

    def store_checkbox_states(self) -> Dict[str, int]:
        states = {}
        self.store_checkbox_states_recursive(self.model.invisibleRootItem(), states)
        return states

    def store_checkbox_states_recursive(
        self, parent: QStandardItem, states: Dict[str, int]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            path = item.data(Qt.UserRole)
            states[path] = item.checkState()
            if item.hasChildren():
                self.store_checkbox_states_recursive(item, states)

    def restore_checkbox_states(self, states: Dict[str, int]):
        self.restore_checkbox_states_recursive(self.model.invisibleRootItem(), states)

    def restore_checkbox_states_recursive(
        self, parent: QStandardItem, states: Dict[str, int]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            path = item.data(Qt.UserRole)
            if path in states:
                item.setCheckState(states[path])
            if item.hasChildren():
                self.restore_checkbox_states_recursive(item, states)

    def store_expansion_states(self) -> Dict[str, bool]:
        states = {}
        self.store_expansion_states_recursive(self.model.invisibleRootItem(), states)
        return states

    def store_expansion_states_recursive(
        self, parent: QStandardItem, states: Dict[str, bool]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            index = self.proxy_model.mapFromSource(item.index())
            states[item.data(Qt.UserRole)] = self.tree_view.isExpanded(index)
            if item.hasChildren():
                self.store_expansion_states_recursive(item, states)

    def restore_expansion_states(self, states: Dict[str, bool]):
        self.restore_expansion_states_recursive(self.model.invisibleRootItem(), states)

    def restore_expansion_states_recursive(
        self, parent: QStandardItem, states: Dict[str, bool]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            index = self.proxy_model.mapFromSource(item.index())
            if item.data(Qt.UserRole) in states:
                self.tree_view.setExpanded(index, states[item.data(Qt.UserRole)])
            if item.hasChildren():
                self.restore_expansion_states_recursive(item, states)

    def store_readonly_expansion_states(self) -> Dict[str, bool]:
        states = {}
        self.store_readonly_expansion_states_recursive(
            self.readonly_model.invisibleRootItem(), states
        )
        return states

    def store_readonly_expansion_states_recursive(
        self, parent: QStandardItem, states: Dict[str, bool]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            index = self.readonly_proxy_model.mapFromSource(item.index())
            states[item.data(Qt.UserRole)] = self.readonly_tree_view.isExpanded(index)
            if item.hasChildren():
                self.store_readonly_expansion_states_recursive(item, states)

    def restore_readonly_expansion_states(self, states: Dict[str, bool]):
        self.restore_readonly_expansion_states_recursive(
            self.readonly_model.invisibleRootItem(), states
        )

    def restore_readonly_expansion_states_recursive(
        self, parent: QStandardItem, states: Dict[str, bool]
    ):
        for row in range(parent.rowCount()):
            item = parent.child(row)
            index = self.readonly_proxy_model.mapFromSource(item.index())
            if item.data(Qt.UserRole) in states:
                self.readonly_tree_view.setExpanded(
                    index, states[item.data(Qt.UserRole)]
                )
            if item.hasChildren():
                self.restore_readonly_expansion_states_recursive(item, states)

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
        selected_files = self.get_checked_files(self.model.invisibleRootItem())
        selected_files += list(self.readonly_files)

        if not selected_files:
            QMessageBox.warning(
                self, "No Files Selected", "Please select at least one file to copy."
            )
            return

        formatted_content = ""
        for file_path in selected_files:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    file_format = Path(file_path).suffix[1:]
                    formatted_content += (
                        f"{file_path}\n```{file_format}\n{content}\n```\n"
                    )
            except Exception as e:
                traceback.print_exc()  # Print full traceback to the console
                QMessageBox.warning(
                    self, "Error", f"Error reading file {file_path}: {str(e)}"
                )
                return

        clipboard = QApplication.clipboard()
        clipboard.setText(formatted_content)

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if index.isValid():
            item = self.model.itemFromIndex(self.proxy_model.mapToSource(index))
            file_path = item.data(Qt.UserRole)

            menu = QMenu(self)
            if item.hasChildren():
                add_folder_action = menu.addAction("Add folder to Read-only")
                add_folder_action.triggered.connect(
                    lambda: self.add_folder_to_readonly(file_path)
                )
            else:
                add_action = menu.addAction("Add to Read-only")
                add_action.triggered.connect(lambda: self.add_to_readonly(file_path))

            menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def add_to_readonly(self, file_path):
        if file_path not in self.readonly_tree_files:
            self.readonly_tree_files.add(file_path)
            self.readonly_files.add(file_path)  # Ensure it's in readonly_files
            self.populate_readonly_tree(Path(self.dir_input.text()))
            self.save_preset()  # Save preset after modification
            self.update_aider_files_json()

    def add_folder_to_readonly(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in self.readonly_tree_files:
                    self.readonly_tree_files.add(file_path)
                    self.readonly_files.add(file_path)  # Ensure it's in readonly_files
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.save_preset()  # Save preset after modification
        self.update_aider_files_json()

    def populate_readonly_tree(self, directory: Path):
        # Disconnect signal to prevent recursion during population
        try:
            self.readonly_model.itemChanged.disconnect(self.on_readonly_item_changed)
        except TypeError:
            pass

        self.readonly_model.clear()
        root_item = self.readonly_model.invisibleRootItem()
        for file_path in sorted(self.readonly_tree_files):
            relative_path = os.path.relpath(file_path, directory)
            path_parts = relative_path.split(os.sep)
            self.add_readonly_item(root_item, path_parts, file_path, str(directory))

        # Update parent check states after populating the tree
        self.update_readonly_parent_check_state_recursive(root_item)

        # Connect the signal after populating
        self.readonly_model.itemChanged.connect(self.on_readonly_item_changed)

    def add_readonly_item(
        self,
        parent: QStandardItem,
        path_parts: List[str],
        full_path: str,
        current_path: str,
    ):
        if not path_parts:
            return
        part = path_parts[0]
        child = self.find_child(parent, part)
        new_current_path = os.path.join(current_path, part)

        if child is None:
            child = QStandardItem(part)
            child.setEditable(False)
            child.setCheckable(True)
            # Set check state based on whether the file is in self.readonly_files
            if full_path in self.readonly_files:
                child.setCheckState(Qt.Checked)
            else:
                child.setCheckState(Qt.Unchecked)
            parent.appendRow(child)
        child.setData(new_current_path, Qt.UserRole)  # Store full path
        if len(path_parts) > 1:
            self.add_readonly_item(child, path_parts[1:], full_path, new_current_path)

    def find_child(self, parent: QStandardItem, text: str) -> Optional[QStandardItem]:
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.text() == text:
                return child
        return None

    def on_readonly_item_changed(self, item):
        try:
            self.readonly_model.itemChanged.disconnect(self.on_readonly_item_changed)
            self.update_readonly_item_check_state(item)
            # Update readonly_files based on the current check states
            self.readonly_files = self.get_readonly_checked_files(
                self.readonly_model.invisibleRootItem()
            )
            self.update_aider_files_json()
        except Exception as e:
            traceback.print_exc()  # Print full traceback to the console
            QMessageBox.warning(
                self, "Error", f"An unexpected error occurred: {str(e)}"
            )
        finally:
            self.readonly_model.itemChanged.connect(self.on_readonly_item_changed)

    def update_readonly_item_check_state(self, item):
        check_state = item.checkState()
        self.set_readonly_children_check_state(item, check_state)
        self.update_readonly_parent_check_state(item)

    def set_readonly_children_check_state(
        self, item: QStandardItem, check_state: Qt.CheckState
    ):
        for row in range(item.rowCount()):
            child = item.child(row)
            child.setCheckState(check_state)
            if child.hasChildren():
                self.set_readonly_children_check_state(child, check_state)

    def update_readonly_parent_check_state(self, item: QStandardItem):
        parent = item.parent()
        if parent is None:
            return
        checked = 0
        unchecked = 0
        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child.checkState() == Qt.Checked:
                checked += 1
            elif child.checkState() == Qt.Unchecked:
                unchecked += 1
        if checked == parent.rowCount():
            parent.setCheckState(Qt.Checked)
        elif unchecked == parent.rowCount():
            parent.setCheckState(Qt.Unchecked)
        else:
            parent.setCheckState(Qt.PartiallyChecked)
        self.update_readonly_parent_check_state(parent)

    def get_readonly_checked_files(self, parent: QStandardItem) -> Set[str]:
        checked_files = set()
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item.checkState() == Qt.Checked:
                file_path = item.data(Qt.UserRole)
                if file_path:
                    checked_files.add(file_path)
                if item.hasChildren():
                    checked_files.update(self.get_readonly_checked_files(item))
            elif item.checkState() == Qt.PartiallyChecked:
                if item.hasChildren():
                    checked_files.update(self.get_readonly_checked_files(item))
        return checked_files

    def show_readonly_context_menu(self, position):
        index = self.readonly_tree_view.indexAt(position)
        if index.isValid():
            item = self.readonly_model.itemFromIndex(
                self.readonly_proxy_model.mapToSource(index)
            )
            file_path = item.data(Qt.UserRole)

            menu = QMenu(self)
            if item.hasChildren():
                remove_action = menu.addAction("Remove folder from Read-only")
                remove_action.triggered.connect(
                    lambda: self.remove_folder_from_readonly(item)
                )
            else:
                remove_action = menu.addAction("Remove from Read-only")
                remove_action.triggered.connect(
                    lambda: self.remove_from_readonly(file_path)
                )

            menu.exec_(self.readonly_tree_view.viewport().mapToGlobal(position))

    def remove_from_readonly(self, file_path):
        self.readonly_tree_files.discard(file_path)
        self.readonly_files.discard(file_path)
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.save_preset()  # Save preset after modification
        self.update_aider_files_json()

    def remove_folder_from_readonly(self, item: QStandardItem):
        self.remove_readonly_children(item)
        self.populate_readonly_tree(Path(self.dir_input.text()))
        self.save_preset()  # Save preset after modification
        self.update_aider_files_json()

    def remove_readonly_children(self, item: QStandardItem):
        for row in range(item.rowCount()):
            child = item.child(row)
            self.remove_readonly_children(child)
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.readonly_tree_files.discard(file_path)
            self.readonly_files.discard(file_path)

    def on_search_text_changed(self, text):
        self.search_timer.stop()
        self.search_timer.start(300)

    def apply_filter(self):
        search_text = self.search_bar.text()
        self.proxy_model.setFilterRegExp(search_text)
        self.readonly_proxy_model.setFilterRegExp(search_text)  # Added this line

        if search_text:
            # Expand all nodes to show all matching items
            self.tree_view.expandAll()
            self.readonly_tree_view.expandAll()
        else:
            # Restore expansion states from preset
            self.restore_expansion_states(self.preset_expansion_states)
            self.restore_readonly_expansion_states(
                self.preset_readonly_expansion_states
            )  # Added this line

    def clear_search(self):
        self.search_bar.clear()
        self.proxy_model.setFilterRegExp("")
        self.readonly_proxy_model.setFilterRegExp(
            ""
        )  # Clear filter on readonly tree as well
        # Restore expansion states when search is cleared
        self.restore_expansion_states(self.preset_expansion_states)
        self.restore_readonly_expansion_states(
            self.preset_readonly_expansion_states
        )  # Added this line

    def close_application(self):
        sys.exit(0)

    def save_preset(self):
        self.save_preset_to_file(self.preset_file_path)

    def save_preset_to_file(self, filename):
        if not self.search_bar.text():
            expansion_states = self.store_expansion_states()
            readonly_expansion_states = (
                self.store_readonly_expansion_states()
            )  # Added this line
        else:
            expansion_states = self.preset_expansion_states
            readonly_expansion_states = (
                self.preset_readonly_expansion_states
            )  # Added this line
        preset_data = {
            "directory": self.dir_input.text(),
            "formats": self.format_input.text(),
            "expansion_states": expansion_states,
            "readonly_expansion_states": readonly_expansion_states,  # Added this line
            "readonly_tree_files": list(self.readonly_tree_files),  # Added
            "readonly_files": list(self.readonly_files),  # Added
        }
        try:
            with open(filename, "w") as f:
                json.dump(preset_data, f, indent=2)
            self.preset_expansion_states = expansion_states
            self.preset_readonly_expansion_states = (
                readonly_expansion_states  # Added this line
            )
        except Exception as e:
            traceback.print_exc()  # Print full traceback to the console
            QMessageBox.warning(self, "Error", f"Failed to save preset: {str(e)}")

    def load_preset(self):
        filename = self.preset_file_path
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    preset_data = json.load(f)
                self.dir_input.setText(preset_data["directory"])
                self.format_input.setText(preset_data["formats"])
                self.preset_expansion_states = preset_data.get("expansion_states", {})
                self.preset_readonly_expansion_states = preset_data.get(
                    "readonly_expansion_states", {}
                )  # Added this line
                self.readonly_tree_files = set(
                    preset_data.get("readonly_tree_files", [])
                )
                self.readonly_files = set(preset_data.get("readonly_files", []))
                self.scan_directory()
                self.restore_expansion_states(self.preset_expansion_states)
                self.repopulate_readonly_tree()  # Added
                self.restore_readonly_expansion_states(
                    self.preset_readonly_expansion_states
                )  # Added this line
            except Exception as e:
                traceback.print_exc()  # Print full traceback to the console
                QMessageBox.warning(self, "Error", f"Failed to load preset: {str(e)}")

    def repopulate_readonly_tree(self):
        self.populate_readonly_tree(Path(self.dir_input.text()))

    def on_tree_expanded(self, index):
        if not self.search_bar.text():
            self.save_preset()

    def on_tree_collapsed(self, index):
        if not self.search_bar.text():
            self.save_preset()

    def on_readonly_tree_expanded(self, index):
        if not self.search_bar.text():
            self.save_preset()

    def on_readonly_tree_collapsed(self, index):
        if not self.search_bar.text():
            self.save_preset()

    def on_format_input_changed(self, text):
        self.save_preset()
        self.scan_directory()

    def count_all_files(self, parent: QStandardItem) -> int:
        count = 0
        for row in range(parent.rowCount()):
            item = parent.child(row)
            if item.hasChildren():
                count += self.count_all_files(item)
            else:
                count += 1
        return count

    # Added method to update parent check states recursively
    def update_readonly_parent_check_state_recursive(self, item: QStandardItem):
        if item.hasChildren():
            for row in range(item.rowCount()):
                child = item.child(row)
                self.update_readonly_parent_check_state_recursive(child)
            # Now update this item's check state based on children's states
            checked = 0
            unchecked = 0
            for row in range(item.rowCount()):
                child = item.child(row)
                state = child.checkState()
                if state == Qt.Checked:
                    checked += 1
                elif state == Qt.Unchecked:
                    unchecked += 1
            if checked == item.rowCount():
                item.setCheckState(Qt.Checked)
            elif unchecked == item.rowCount():
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.PartiallyChecked)


def signal_handler(signum, frame):
    sys.exit(0)


if __name__ == "__main__":
    # Set the global exception handler
    sys.excepthook = handle_exception

    # Optionally, handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    args = parse_arguments()
    working_directory = args.directory or DEFAULT_DIRECTORY

    try:
        app = QApplication(sys.argv)
        ex = AiderFileGUIApp(working_directory)
        ex.show()
        sys.exit(app.exec_())
    except Exception:
        # Catch any exceptions that occur during the initialization phase
        traceback.print_exc()  # Print full traceback to the console
        QMessageBox.critical(
            None,
            "Fatal Error",
            "An unexpected error occurred. The application will exit.",
        )
        sys.exit(1)
