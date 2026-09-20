"""One reentrant process-wide lock for this memory-constrained R workload."""
from contextlib import contextmanager
import fcntl
from pathlib import Path
import threading

ROOT=Path(__file__).resolve().parents[1]
_thread_lock=threading.RLock()
_depth=0
_stream=None


@contextmanager
def scientific_execution():
    global _depth, _stream
    with _thread_lock:
        if _depth==0:
            (ROOT/"results").mkdir(exist_ok=True)
            _stream=(ROOT/"results/r-execution.lock").open("a")
            fcntl.flock(_stream,fcntl.LOCK_EX)
        _depth+=1
        try:
            yield
        finally:
            _depth-=1
            if _depth==0:
                _stream.close()
                _stream=None
