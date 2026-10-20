import subprocess
import tempfile
import threading

ACTIVE = set()
ACTIVE_LOCK = threading.Lock()


def stop_processes():
    with ACTIVE_LOCK:
        processes = list(ACTIVE)
    for process in processes:
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
    for process in processes:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class Cancelled(RuntimeError):
    pass


def check_cancel(cancel):
    if cancel and cancel():
        raise Cancelled('Đã hủy tác vụ.')


def execute(command, cwd=None, cancel=None, timeout=1800, env=None):
    # A file avoids stderr-pipe deadlock while long FFmpeg/model jobs run.
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        with ACTIVE_LOCK:
            ACTIVE.add(process)
        import time
        start = time.monotonic()
        try:
            while process.poll() is None:
                check_cancel(cancel)
                if time.monotonic() - start > timeout:
                    raise TimeoutError('Lệnh chạy quá thời gian cho phép.')
                time.sleep(.1)
            if process.returncode:
                log.seek(0, 2)
                length = log.tell()
                log.seek(max(0, length - 6000))
                raise RuntimeError(log.read().decode('utf-8', errors='replace'))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            with ACTIVE_LOCK:
                ACTIVE.discard(process)
