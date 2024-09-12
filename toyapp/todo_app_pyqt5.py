
import sys
import redis
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QMessageBox, QProgressBar,
    QComboBox, QLabel, QInputDialog, QMenu
)
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer

# Create Redis client
redis_client = redis.Redis(
    host="game-jennet-47074.upstash.io",
    port=6379,
    password="AbfiAAIjcDFjZmI2NDBiOTgwY2M0Njk4OWM0NDE0ZDEzYmVjNWEzMHAxMA",
    ssl=True,
)

class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.redis = redis_client
            self.redis.ping()  # Test the connection
            self.task_counter_key = "task_counter"
            self.tasks_hash_key = "tasks"
            self.dark_mode = False
            self.initUI()
            self.load_tasks()
        except redis.RedisError as e:
            self.show_error("Redis Connection Error", f"Failed to connect to Redis: {str(e)}")
            self.redis = None

    def initUI(self):
        self.setWindowTitle("TODO App")
        self.setGeometry(100, 100, 500, 500)

        layout = QVBoxLayout()

        # Dark mode toggle
        self.dark_mode_button = QPushButton("Toggle Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        layout.addWidget(self.dark_mode_button)

        # Input field, category dropdown, priority dropdown, and Add button
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.category_dropdown = QComboBox()
        self.category_dropdown.addItems(["Work", "Personal", "Shopping", "Other"])
        self.priority_dropdown = QComboBox()
        self.priority_dropdown.addItems(["Low", "Medium", "High"])
        self.add_button = QPushButton("Add Task")
        self.add_button.clicked.connect(self.add_task)
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.category_dropdown)
        input_layout.addWidget(self.priority_dropdown)
        input_layout.addWidget(self.add_button)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search tasks...")
        self.search_bar.textChanged.connect(self.filter_tasks)

        # Task list
        self.task_list = QListWidget()
        self.task_list.setDragDropMode(QListWidget.InternalMove)
        self.task_list.dropEvent = self.dropEvent

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        # Delete completed tasks button
        self.delete_completed_button = QPushButton("Delete Completed Tasks")
        self.delete_completed_button.clicked.connect(self.delete_completed_tasks)

        # Today's tasks button
        self.today_tasks_button = QPushButton("Today's Tasks")
        self.today_tasks_button.clicked.connect(self.show_today_tasks)

        layout.addLayout(input_layout)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.task_list)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.delete_completed_button)
        layout.addWidget(self.today_tasks_button)

        self.setLayout(layout)

        # Set up tooltips
        self.add_button.setToolTip("Add a new task")
        self.delete_completed_button.setToolTip("Delete all completed tasks")
        self.today_tasks_button.setToolTip("Show tasks due today")
        self.dark_mode_button.setToolTip("Toggle between light and dark mode")
        self.search_bar.setToolTip("Search for tasks")
        self.category_dropdown.setToolTip("Select task category")
        self.priority_dropdown.setToolTip("Select task priority")

        # Set up keyboard shortcuts
        self.add_button.setShortcut("Ctrl+N")
        self.delete_completed_button.setShortcut("Ctrl+D")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.update_style()

    def update_style(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget { background-color: #2b2b2b; color: #ffffff; }
                QPushButton { background-color: #4a4a4a; border: 1px solid #5a5a5a; }
                QLineEdit, QComboBox { background-color: #3a3a3a; border: 1px solid #5a5a5a; }
                QListWidget { background-color: #3a3a3a; border: 1px solid #5a5a5a; }
                QProgressBar { background-color: #3a3a3a; border: 1px solid #5a5a5a; }
            """)
        else:
            self.setStyleSheet("")

    def load_tasks(self):
        try:
            tasks = self.redis.hgetall(self.tasks_hash_key)
            for task_id, task_data in tasks.items():
                task_data = task_data.decode('utf-8')
                task_text, completed, category, priority = task_data.split('|')
                self.add_task_to_list(task_id, task_text, completed == 'True', category, priority)
            self.update_progress_bar()
        except redis.RedisError as e:
            self.show_error("Error loading tasks", str(e))

    def get_next_task_id(self):
        try:
            return self.redis.incr(self.task_counter_key)
        except redis.RedisError as e:
            self.show_error("Error generating task ID", str(e))
            return None

    def add_task(self):
        task_text = self.task_input.text().strip()
        if task_text:
            task_id = self.get_next_task_id()
            if task_id is not None:
                try:
                    category = self.category_dropdown.currentText()
                    priority = self.priority_dropdown.currentText()
                    self.redis.hset(self.tasks_hash_key, task_id, f"{task_text}|False|{category}|{priority}")
                    self.add_task_to_list(task_id, task_text, False, category, priority)
                    self.task_input.clear()
                    self.update_progress_bar()
                except redis.RedisError as e:
                    self.show_error("Error adding task", str(e))

    def add_task_to_list(self, task_id, task_text, completed, category, priority):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout()
        checkbox = QCheckBox(task_text)
        checkbox.setChecked(completed)
        checkbox.stateChanged.connect(lambda state, tid=task_id: self.update_task_status(tid, state))
        category_label = QLabel(f"[{category}]")
        priority_label = QLabel(f"({priority})")
        layout.addWidget(checkbox)
        layout.addWidget(category_label)
        layout.addWidget(priority_label)
        widget.setLayout(layout)
        item.setSizeHint(widget.sizeHint())
        self.task_list.addItem(item)
        self.task_list.setItemWidget(item, widget)
        self.animate_task_addition(item)
        self.update_task_color(item, priority)

    def animate_task_addition(self, item):
        animation = QPropertyAnimation(item, b"background")
        animation.setDuration(500)
        animation.setStartValue(QColor("#ADFF2F"))
        animation.setEndValue(QColor(0, 0, 0, 0))
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()

    def update_task_color(self, item, priority):
        color = QColor("#FFFFFF") if self.dark_mode else QColor("#000000")
        if priority == "High":
            color = QColor("#FF4500")
        elif priority == "Medium":
            color = QColor("#FFA500")
        item.setForeground(color)

    def update_task_status(self, task_id, state):
        try:
            task_data = self.redis.hget(self.tasks_hash_key, task_id)
            if task_data:
                task_data = task_data.decode('utf-8')
                task_text, _, category, priority = task_data.split('|')
                self.redis.hset(self.tasks_hash_key, task_id, f"{task_text}|{state == 2}|{category}|{priority}")
                self.update_progress_bar()
        except redis.RedisError as e:
            self.show_error("Error updating task status", str(e))

    def delete_completed_tasks(self):
        reply = QMessageBox.question(self, 'Confirm Deletion', 
                                     "Are you sure you want to delete all completed tasks?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                tasks = self.redis.hgetall(self.tasks_hash_key)
                for task_id, task_data in tasks.items():
                    task_data = task_data.decode('utf-8')
                    _, completed, _, _ = task_data.split('|')
                    if completed == 'True':
                        self.redis.hdel(self.tasks_hash_key, task_id)

                for i in range(self.task_list.count() - 1, -1, -1):
                    item = self.task_list.item(i)
                    widget = self.task_list.itemWidget(item)
                    checkbox = widget.layout().itemAt(0).widget()
                    if checkbox.isChecked():
                        self.animate_task_deletion(item)
                self.update_progress_bar()
            except redis.RedisError as e:
                self.show_error("Error deleting completed tasks", str(e))

    def animate_task_deletion(self, item):
        animation = QPropertyAnimation(item, b"background")
        animation.setDuration(500)
        animation.setStartValue(QColor("#FF6347"))
        animation.setEndValue(QColor(0, 0, 0, 0))
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(lambda: self.task_list.takeItem(self.task_list.row(item)))
        animation.start()

    def update_progress_bar(self):
        total_tasks = self.task_list.count()
        completed_tasks = sum(1 for i in range(total_tasks) if self.task_list.itemWidget(self.task_list.item(i)).layout().itemAt(0).widget().isChecked())
        progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        self.progress_bar.setValue(int(progress))

    def filter_tasks(self):
        search_text = self.search_bar.text().lower()
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            task_text = widget.layout().itemAt(0).widget().text().lower()
            category = widget.layout().itemAt(1).widget().text().lower()
            priority = widget.layout().itemAt(2).widget().text().lower()
            item.setHidden(search_text not in task_text and search_text not in category and search_text not in priority)

    def show_today_tasks(self):
        # For simplicity, we'll just show all tasks
        # In a real app, you'd filter tasks based on their due date
        for i in range(self.task_list.count()):
            self.task_list.item(i).setHidden(False)

    def dropEvent(self, event):
        super(QListWidget, self.task_list).dropEvent(event)
        self.update_task_order()

    def update_task_order(self):
        # Update the order of tasks in Redis
        # This is a placeholder and would need to be implemented
        pass

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    todo_app = TodoApp()
    todo_app.show()
    sys.exit(app.exec_())
