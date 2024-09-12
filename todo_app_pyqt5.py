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
from redis_config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_HASH_KEY


class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize Redis connection
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        self.initUI()
        # Load existing tasks from Redis
        self.load_tasks_from_redis()

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def update_task_status(self, task_text, completed):
        try:
            self.redis_client.hset(REDIS_HASH_KEY, task_text, int(completed))
        except redis.RedisError as e:
            self.show_error_message(f"Failed to update task status: {str(e)}")

    def closeEvent(self, event):
        # Close Redis connection when the app is closed
        self.redis_client.close()
        super().closeEvent(event)

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

    def add_task(self):
        task_text = self.task_input.text().strip()
        if task_text:
            item = QListWidgetItem()
            self.task_list.addItem(item)
            checkbox = QCheckBox(task_text)
            checkbox.stateChanged.connect(lambda state: self.update_task_status(task_text, state == 2))
            self.task_list.setItemWidget(item, checkbox)
            self.task_input.clear()
            self.store_task_in_redis(task_text)

    def store_task_in_redis(self, task_text, completed=False):
        # Store a task in Redis hash
        try:
            self.redis_client.hset(REDIS_HASH_KEY, task_text, int(completed))
        except redis.RedisError as e:
            self.show_error_message(f"Failed to store task: {str(e)}")

    def load_tasks_from_redis(self):
        # Load all tasks from Redis and populate the UI
        try:
            tasks = self.redis_client.hgetall(REDIS_HASH_KEY)
            for task_text, completed in tasks.items():
                item = QListWidgetItem()
                self.task_list.addItem(item)
                checkbox = QCheckBox(task_text.decode())
                checkbox.setChecked(bool(int(completed)))
                checkbox.stateChanged.connect(lambda state, text=task_text.decode(): self.update_task_status(text, state == 2))
                self.task_list.setItemWidget(item, checkbox)
        except redis.RedisError as e:
            self.show_error_message(f"Failed to load tasks: {str(e)}")

    def delete_completed_tasks(self):
        # Delete completed tasks from both UI and Redis
        try:
            with self.redis_client.pipeline() as pipe:
                for i in range(self.task_list.count() - 1, -1, -1):
                    item = self.task_list.item(i)
                    checkbox = self.task_list.itemWidget(item)
                    if checkbox.isChecked():
                        task_text = checkbox.text()
                        self.task_list.takeItem(i)
                        pipe.hdel(REDIS_HASH_KEY, task_text)
                pipe.execute()
        except redis.RedisError as e:
            self.show_error_message(f"Failed to delete completed tasks: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    todo_app = TodoApp()
    todo_app.show()
    sys.exit(app.exec_())
