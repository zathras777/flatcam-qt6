from PyQt6.QtCore import QObject, pyqtSignal, QThread
import multiprocessing

from FlatCAMWorker import Worker


class WorkerStack(QObject):

    worker_task = pyqtSignal(dict)               # 'worker_name', 'func', 'params'
    thread_exception = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.workers = []
        self.threads = []
        self.load = {}                                  # {'worker_name': tasks_count}

        # Create workers crew
        for i in range(0, 2):
            worker = Worker(self, 'Slogger-' + str(i))
            thread = QThread()

            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.task_completed.connect(self.on_task_completed)

            thread.start()

            self.workers.append(worker)
            self.threads.append(thread)
            self.load[worker.name] = 0

    def __del__(self):
        for thread in self.threads:
            thread.terminate()

    def add_task(self, task):
        worker_name = min(self.load, key=self.load.get)
        self.load[worker_name] += 1
        self.worker_task.emit({'worker_name': worker_name, 'fcn': task['fcn'], 'params': task['params']})

    def on_task_completed(self, worker_name):
        self.load[str(worker_name)] -= 1
