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

def save_task_to_redis(task_id, task_data):
    redis_client.hset(f'task:{task_id}', mapping=task_data)

def get_task_from_redis(task_id):
    return redis_client.hgetall(f'task:{task_id}')

def delete_task_from_redis(task_id):
    redis_client.delete(f'task:{task_id}')

def add_task_to_sorted_set(task_id):
    redis_client.zadd('task_order', {task_id: time.time()})

def remove_task_from_sorted_set(task_id):
    redis_client.zrem('task_order', task_id)

def get_task_order():
    return redis_client.zrange('task_order', 0, -1)

def get_task_state_bit(task_id, state_bit):
    task_data = get_task_from_redis(task_id)
    return bool(int(task_data.get(f'state_{state_bit}', 0)))

def set_task_state_bit(task_id, state_bit, value):
    task_data = get_task_from_redis(task_id)
    task_data[f'state_{state_bit}'] = int(value)
    save_task_to_redis(task_id, task_data)


class TodoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_tasks_from_redis()

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
            task_data = {
                'text': task_text,
                'state_0': 0,  # Not completed
                'state_1': 0   # Not important
            }
            with redis_client.pipeline() as pipe:
                pipe.hset(f'task:{task_id}', mapping=task_data)
                pipe.zadd('task_order', {task_id: time.time()})
                pipe.execute()
            self.add_task_to_gui(task_id, task_data)
            self.task_input.clear()

    def delete_completed_tasks(self):
        completed_tasks = []
        for i in range(self.task_list.count() - 1, -1, -1):
            item = self.task_list.item(i)
            task_id = item.data(Qt.UserRole)
            if self.get_task_state_cached(task_id, TASK_STATE_COMPLETED):
                completed_tasks.append(task_id)
                self.task_list.takeItem(i)

        if completed_tasks:
            with redis_client.pipeline() as pipe:
                for task_id in completed_tasks:
                    pipe.delete(f'task:{task_id}')
                    pipe.zrem('task_order', task_id)
                pipe.execute()

    def get_all_tasks(self):
        tasks = []
        for task_id in get_task_order():
            task_data = get_task_from_redis(task_id.decode('utf-8'))
            tasks.append({
                'id': task_id.decode('utf-8'),
                'text': task_data[b'text'].decode('utf-8'),
                'completed': bool(int(task_data[b'state_0'])),
                'important': bool(int(task_data[b'state_1']))
            })
        return tasks

    def get_task_state_cached(self, task_id, state_bit):
        task_data = get_task_from_redis(task_id)
        return bool(int(task_data.get(f'state_{state_bit}', 0)))

    def set_task_state_cached(self, task_id, state_bit, value):
        task_data = get_task_from_redis(task_id)
        task_data[f'state_{state_bit}'] = int(value)
        save_task_to_redis(task_id, task_data)

    def load_tasks_from_redis(self):
        for task_id in get_task_order():
            task_data = get_task_from_redis(task_id.decode('utf-8'))
            self.add_task_to_gui(task_id.decode('utf-8'), task_data)

    def add_task_to_gui(self, task_id, task_data):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, task_id)
        self.task_list.addItem(item)
        checkbox = QCheckBox(task_data[b'text'].decode('utf-8'))
        checkbox.setChecked(bool(int(task_data[b'state_0'])))
        self.task_list.setItemWidget(item, checkbox)

    def closeEvent(self, event):
        save_tasks_to_redis(self.get_all_tasks())
        super().closeEvent(event)

    def filter_tasks(self, state_bit, value):
        filtered_tasks = []
        for task_id in get_task_order():
            task_data = get_task_from_redis(task_id.decode('utf-8'))
            if bool(int(task_data[f'state_{state_bit}'.encode()])) == value:
                filtered_tasks.append({
                    'id': task_id.decode('utf-8'),
                    'text': task_data[b'text'].decode('utf-8'),
                    'completed': bool(int(task_data[b'state_0'])),
                    'important': bool(int(task_data[b'state_1']))
                })
        return filtered_tasks

    def closeEvent(self, event):
        # No need to save tasks explicitly as they're saved in real-time
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    todo_app = TodoApp()
    todo_app.show()
    sys.exit(app.exec_())
