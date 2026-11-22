"""Background execution helpers (keeps the UI responsive)."""
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from services.docx_service import Cancelled

log = logging.getLogger(__name__)


class WorkerSignals(QObject):
    progress = Signal(int, int, str)
    item = Signal(object)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()
    finished = Signal()


class Worker(QRunnable):
    """Runs ``fn(worker, *args, **kwargs)`` in the global thread pool.

    *fn* receives the worker so it can report progress
    (``worker.signals.progress.emit``) and check ``worker.cancel_event``.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.cancel_event = threading.Event()
        self.setAutoDelete(False)

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:  # executed in a pool thread
        try:
            res = self.fn(self, *self.args, **self.kwargs)
        except Cancelled:
            self.signals.cancelled.emit()
        except Exception as e:  # report every failure to the UI
            log.exception("Background task failed")
            self.signals.error.emit(str(e) or e.__class__.__name__)
        else:
            if self.cancel_event.is_set():
                self.signals.cancelled.emit()
            else:
                self.signals.result.emit(res)
        finally:
            self.signals.finished.emit()


class TaskRunner(QObject):
    """Keeps Python references to running workers until they finish."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active: set[Worker] = set()
        self.pool = QThreadPool.globalInstance()

    def start(self, worker: Worker) -> Worker:
        self._active.add(worker)
        worker.signals.finished.connect(lambda w=worker: self._active.discard(w))
        self.pool.start(worker)
        return worker

    def busy(self) -> bool:
        return bool(self._active)

    def cancel_all(self) -> None:
        for w in list(self._active):
            w.cancel()

    def wait(self, msecs: int = 5000) -> None:
        self.pool.waitForDone(msecs)
