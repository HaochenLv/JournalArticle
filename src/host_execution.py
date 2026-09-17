"""Host execution helpers; no simulator, evaluator or experimental policy changes."""
import ctypes
import multiprocessing
import os
import platform
import subprocess
import time
from ctypes import wintypes


def _invoke(sender, function, args):
    try:
        sender.send(('ok', function(*args)))
    except Exception as error:
        sender.send(('error', type(error).__name__, str(error)))
    finally:
        sender.close()


def spawned_call(function, args, timeout_s):
    """Run one call with an actual killable wall deadline, including spawn overhead."""
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_invoke, args=(sender, function, args))
    deadline = time.monotonic() + timeout_s
    try:
        process.start()
        sender.close()
        if not receiver.poll(max(0., deadline - time.monotonic())):
            raise TimeoutError('formal reference wall timeout')
        try:
            result = receiver.recv()
        except EOFError as error:
            raise RuntimeError('reference child exited without a result') from error
        process.join(max(0., deadline - time.monotonic()))
        if process.is_alive():
            raise TimeoutError('formal reference wall timeout')
        if result[0] == 'error':
            raise RuntimeError(result[1] + ': ' + result[2])
        if process.exitcode:
            raise RuntimeError('reference child exit code ' + str(process.exitcode))
        return result[1]
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join()
            process.close()
        receiver.close()
        sender.close()


def process_alive(pid):
    """Read process state; os.kill(pid, 0) must never be used on Windows."""
    if pid <= 0:
        raise ValueError('Expected a positive process ID')
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # PID no longer exists
            return False
        raise ctypes.WinError(error)
    try:
        result = kernel.WaitForSingleObject(handle, 0)
        if result == 0:
            return False
        if result == 258:  # WAIT_TIMEOUT: process is still running
            return True
        raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def host_memory_bytes():
    if os.name == 'nt':
        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (name, ctypes.c_ulonglong) for name in
                ('physical', 'available', 'pagefile', 'available_pagefile',
                 'virtual', 'available_virtual', 'extended')]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MemoryStatus)]
        kernel.GlobalMemoryStatusEx.restype = wintypes.BOOL
        if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise ctypes.WinError(ctypes.get_last_error())
        return status.physical
    if platform.system() == 'Darwin':
        return int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']))
    if hasattr(os, 'sysconf'):
        try:
            return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        except (ValueError, OSError):
            pass
    return None


def host_metadata():
    return {'system': platform.system(), 'machine': platform.machine(),
            'python': platform.python_version(), 'cpu_logical': os.cpu_count(),
            'memory_bytes': host_memory_bytes()}
