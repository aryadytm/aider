import sys
import json
import time
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
)
from PyQt5.QtCore import Qt

# Redis connection constants
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Redis connection
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Task state constants
TASK_STATE_COMPLETED = 0
TASK_STATE_IMPORTANT = 1

def serialize_tasks(tasks):
    return json.dumps(tasks)

def deserialize_tasks(tasks_json):
    return json.loads(tasks_json) if tasks_json else []

def save_tasks_to_redis(tasks):
    redis_client.set('tasks', serialize_tasks(tasks))

def load_tasks_from_redis():
    tasks_json = redis_client.get('tasks')
    return deserialize_tasks(tasks_json.decode('utf-8')) if tasks_json else []

def add_task_to_sorted_set(task_id):
    redis_client.zadd('task_order', {task_id: time.time()})

def remove_task_from_sorted_set(task_id):
    redis_client.zrem('task_order', task_id)

def get_task_order():
    return redis_client.zrange('task_order', 0, -1)

def set_task_state_bit(task_id, state_bit, value):
    redis_client.setbit(f'task_states:{state_bit}', int(task_id), int(value))

def get_task_state_bit(task_id, state_bit):
    return bool(redis_client.getbit(f'task_states:{state_bit}', int(task_id)))

def redis_connection_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.ConnectionError:
            print("Error: Could not connect to Redis. Using local storage only.")
            return None
    return wrapper

@redis_connection_decorator
def save_tasks_to_redis(tasks):
    redis_client.set('tasks', serialize_tasks(tasks))

@redis_connection_decorator
def load_tasks_from_redis():
    tasks_json = redis_client.get('tasks')
    return deserialize_tasks(tasks_json.decode('utf-8')) if tasks_json else []


class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.task_cache = {}
        self.initUI()
        try:
            self.load_tasks_from_redis()
        except redis.ConnectionError:
            print("Error: Could not connect to Redis. Starting with an empty task list.")

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
            task_id = str(time.time())
            item = QListWidgetItem()
            item.setData(Qt.UserRole, task_id)
            self.task_list.addItem(item)
            checkbox = QCheckBox(task_text)
            self.task_list.setItemWidget(item, checkbox)
            
            add_task_to_sorted_set(task_id)
            self.set_task_state_cached(task_id, TASK_STATE_COMPLETED, False)
            self.update_cache(task_id, {'id': task_id, 'text': task_text, 'states': {TASK_STATE_COMPLETED: False}})
            save_tasks_to_redis(self.get_all_tasks())
            self.task_input.clear()

    def delete_completed_tasks(self):
        for i in range(self.task_list.count() - 1, -1, -1):
            item = self.task_list.item(i)
            checkbox = self.task_list.itemWidget(item)
            if checkbox.isChecked():
                task_id = item.data(Qt.UserRole)
                self.task_list.takeItem(i)
                remove_task_from_sorted_set(task_id)
                self.remove_from_cache(task_id)
        save_tasks_to_redis(self.get_all_tasks())

    def get_all_tasks(self):
        tasks = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            checkbox = self.task_list.itemWidget(item)
            task_id = item.data(Qt.UserRole)
            tasks.append({
                'id': task_id,
                'text': checkbox.text(),
                'completed': checkbox.isChecked(),
                'states': {
                    TASK_STATE_COMPLETED: self.get_task_state_cached(task_id, TASK_STATE_COMPLETED),
                    TASK_STATE_IMPORTANT: self.get_task_state_cached(task_id, TASK_STATE_IMPORTANT)
                }
            })
        return tasks

    def update_cache(self, task_id, task_data):
        self.task_cache[task_id] = task_data

    def remove_from_cache(self, task_id):
        self.task_cache.pop(task_id, None)

    def get_task_from_cache(self, task_id):
        return self.task_cache.get(task_id)

    def clear_cache(self):
        self.task_cache.clear()

    def get_task_state_cached(self, task_id, state_bit):
        cached_task = self.get_task_from_cache(task_id)
        if cached_task is not None:
            return cached_task['states'].get(state_bit, False)
        return get_task_state_bit(task_id, state_bit)

    def set_task_state_cached(self, task_id, state_bit, value):
        set_task_state_bit(task_id, state_bit, value)
        cached_task = self.get_task_from_cache(task_id)
        if cached_task is not None:
            cached_task['states'][state_bit] = value
            self.update_cache(task_id, cached_task)

    def load_tasks_from_redis(self):
        tasks = load_tasks_from_redis()
        for task in tasks:
            self.add_task_from_data(task)

    def add_task_from_data(self, task_data):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, task_data['id'])
        self.task_list.addItem(item)
        checkbox = QCheckBox(task_data['text'])
        checkbox.setChecked(task_data['completed'])
        self.task_list.setItemWidget(item, checkbox)
        self.update_cache(task_data['id'], task_data)

    def closeEvent(self, event):
        save_tasks_to_redis(self.get_all_tasks())
        super().closeEvent(event)

    def filter_tasks(self, state_bit, value):
        all_tasks = self.get_all_tasks()
        return [task for task in all_tasks if self.get_task_state_cached(task['id'], state_bit) == value]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    todo_app = TodoApp()
    todo_app.show()
    sys.exit(app.exec_())
