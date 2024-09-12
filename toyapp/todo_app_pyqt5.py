
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

# Redis connection constants
REDIS_HOST = "game-jennet-47074.upstash.io"
REDIS_PASSWORD = "AbfiAAIjcDFjZmI2NDBiOTgwY2M0Njk4OWM0NDE0ZDEzYmVjNWEzMHAxMA"
REDIS_PORT = 6379
REDIS_DB = 0

# Create Redis connection URL
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.redis_client = None
        self.connect_to_redis()
        self.initUI()
        self.load_tasks()

    def connect_to_redis(self):
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test the connection
        except redis.ConnectionError:
            QMessageBox.critical(self, "Error", "Failed to connect to Redis. Please check your connection and try again.")
            sys.exit(1)

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

    def generate_task_id(self):
        return self.redis_client.incr("task_id_counter")

    def save_task(self, task_id, task_text, completed=False):
        self.redis_client.hset(f"task:{task_id}", mapping={
            "text": task_text,
            "completed": str(completed)
        })

    def update_task_status(self, task_id, completed):
        self.redis_client.hset(f"task:{task_id}", "completed", str(completed))

    def delete_task(self, task_id):
        self.redis_client.delete(f"task:{task_id}")

    def load_tasks(self):
        task_keys = self.redis_client.keys("task:*")
        for task_key in task_keys:
            task_data = self.redis_client.hgetall(task_key)
            self.add_task_to_ui(task_key.split(":")[1], task_data["text"], task_data["completed"] == "True")

    def add_task_to_ui(self, task_id, task_text, completed=False):
        item = QListWidgetItem()
        self.task_list.addItem(item)
        checkbox = QCheckBox(task_text)
        checkbox.setChecked(completed)
        checkbox.stateChanged.connect(lambda state, tid=task_id: self.update_task_status(tid, state == 2))
        self.task_list.setItemWidget(item, checkbox)
        item.setData(1, task_id)  # Store task_id in item data

    def add_task(self):
        task_text = self.task_input.text().strip()
        if task_text:
            task_id = self.generate_task_id()
            with self.redis_client.pipeline() as pipe:
                pipe.multi()
                self.save_task(task_id, task_text)
                pipe.execute()
            self.add_task_to_ui(task_id, task_text)
            self.task_input.clear()

    def delete_completed_tasks(self):
        for i in range(self.task_list.count() - 1, -1, -1):
            item = self.task_list.item(i)
            checkbox = self.task_list.itemWidget(item)
            if checkbox.isChecked():
                task_id = item.data(1)
                with self.redis_client.pipeline() as pipe:
                    pipe.multi()
                    self.delete_task(task_id)
                    pipe.execute()
                self.task_list.takeItem(i)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        todo_app = TodoApp()
        todo_app.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Error", f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
