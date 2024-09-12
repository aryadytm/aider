
import sys
import redis
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QMessageBox,
)

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
            self.initUI()
            self.load_tasks()
        except redis.RedisError as e:
            self.show_error("Redis Connection Error", f"Failed to connect to Redis: {str(e)}")
            self.redis = None

    def initUI(self):
        self.setWindowTitle("TODO App")
        self.setGeometry(100, 100, 400, 400)

        layout = QVBoxLayout()

        # Input field and Add button
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.add_button = QPushButton("Add Task")
        self.add_button.clicked.connect(self.add_task)
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.add_button)

        # Task list
        self.task_list = QListWidget()

        # Delete completed tasks button
        self.delete_completed_button = QPushButton("Delete Completed Tasks")
        self.delete_completed_button.clicked.connect(self.delete_completed_tasks)

        layout.addLayout(input_layout)
        layout.addWidget(self.task_list)
        layout.addWidget(self.delete_completed_button)

        self.setLayout(layout)

    def load_tasks(self):
        try:
            tasks = self.redis.hgetall(self.tasks_hash_key)
            for task_id, task_data in tasks.items():
                task_data = task_data.decode('utf-8')
                task_text, completed = task_data.split('|')
                item = QListWidgetItem()
                self.task_list.addItem(item)
                checkbox = QCheckBox(task_text)
                checkbox.setChecked(completed == 'True')
                checkbox.stateChanged.connect(lambda state, tid=task_id: self.update_task_status(tid, state))
                self.task_list.setItemWidget(item, checkbox)
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
                    self.redis.hset(self.tasks_hash_key, task_id, f"{task_text}|False")
                    item = QListWidgetItem()
                    self.task_list.addItem(item)
                    checkbox = QCheckBox(task_text)
                    checkbox.stateChanged.connect(lambda state, tid=task_id: self.update_task_status(tid, state))
                    self.task_list.setItemWidget(item, checkbox)
                    self.task_input.clear()
                except redis.RedisError as e:
                    self.show_error("Error adding task", str(e))

    def update_task_status(self, task_id, state):
        try:
            task_data = self.redis.hget(self.tasks_hash_key, task_id)
            if task_data:
                task_data = task_data.decode('utf-8')
                task_text, _ = task_data.split('|')
                self.redis.hset(self.tasks_hash_key, task_id, f"{task_text}|{state == 2}")
        except redis.RedisError as e:
            self.show_error("Error updating task status", str(e))

    def delete_completed_tasks(self):
        try:
            tasks = self.redis.hgetall(self.tasks_hash_key)
            for task_id, task_data in tasks.items():
                task_data = task_data.decode('utf-8')
                _, completed = task_data.split('|')
                if completed == 'True':
                    self.redis.hdel(self.tasks_hash_key, task_id)

            for i in range(self.task_list.count() - 1, -1, -1):
                item = self.task_list.item(i)
                checkbox = self.task_list.itemWidget(item)
                if checkbox.isChecked():
                    self.task_list.takeItem(i)
        except redis.RedisError as e:
            self.show_error("Error deleting completed tasks", str(e))

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    todo_app = TodoApp()
    todo_app.show()
    sys.exit(app.exec_())
