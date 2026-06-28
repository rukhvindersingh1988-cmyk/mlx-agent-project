import json
import os
import sys
from enum import Enum
from datetime import datetime

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class Task:
    def __init__(self, title, priority, description):
        self.title = title
        self.priority = priority
        self.description = description
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.done = False

    def to_dict(self):
        return {
            'title': self.title,
            'priority': self.priority.name,
            'description': self.description,
            'created_at': self.created_at,
            'done': self.done
        }

    @classmethod
    def from_dict(cls, data):
        priority = Priority[data['priority']]
        task = cls(data['title'], priority, data['description'])
        task.created_at = data['created_at']
        task.done = data['done']
        return task

class TaskManager:
    def __init__(self, filename):
        self.filename = filename
        self.tasks = self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                data = json.load(file)
                return [Task.from_dict(task) for task in data]
        else:
            return []

    def save_tasks(self):
        data = [task.to_dict() for task in self.tasks]
        with open(self.filename, 'w') as file:
            json.dump(data, file, indent=4)

    def add_task(self, title, priority, description):
        task = Task(title, priority, description)
        self.tasks.append(task)
        self.save_tasks()

    def delete_task(self, index):
        try:
            del self.tasks[index]
            self.save_tasks()
        except IndexError:
            print('\033[91mInvalid task index.\033[0m')

    def mark_task_as_done(self, index):
        try:
            self.tasks[index].done = True
            self.save_tasks()
        except IndexError:
            print('\033[91mInvalid task index.\033[0m')

    def print_tasks(self):
        for i, task in enumerate(self.tasks):
            priority_color = '\033[91m' if task.priority == Priority.HIGH else '\033[93m' if task.priority == Priority.MEDIUM else '\033[92m'
            done_color = '\033[92m' if task.done else '\033[0m'
            print(f'{i+1}. {priority_color}{task.priority.name}\033[0m - {done_color}{task.title}\033[0m - {task.description}')

def main():
    filename = 'tasks.json'
    task_manager = TaskManager(filename)

    while True:
        print('\033[94m1. Add task\033[0m')
        print('\033[94m2. Delete task\033[0m')
        print('\033[94m3. Mark task as done\033[0m')
        print('\033[94m4. Print tasks\033[0m')
        print('\033[94m5. Exit\033[0m')
        choice = input('> ')

        if choice == '1':
            title = input('Enter task title: ')
            priority = Priority[input('Enter task priority (HIGH/MEDIUM/LOW): ')]
            description = input('Enter task description: ')
            task_manager.add_task(title, priority, description)
        elif choice == '2':
            task_manager.print_tasks()
            index = int(input('Enter task index to delete: ')) - 1
            task_manager.delete_task(index)
        elif choice == '3':
            task_manager.print_tasks()
            index = int(input('Enter task index to mark as done: ')) - 1
            task_manager.mark_task_as_done(index)
        elif choice == '4':
            task_manager.print_tasks()
        elif choice == '5':
            break
        else:
            print('\033[91mInvalid choice.\033[0m')

if __name__ == '__main__':
    main()