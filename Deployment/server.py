import sys
import logging, logging.handlers
import os
from os import path
from contextlib import contextmanager
import win32pipe, win32file, pywintypes, win32event, winerror, win32security

from common import WorkerError, PIPE_NAME, WinPipeSock, EXIT_FAILURE, EXIT_SUCCESS, LOCK_FILE

INBUF_SIZE = 512 * 1024 * 1024 # 512 MB
OUTBUF_SIZE = 64 * 1024 # 64 KB

def setup_logger(name):
    logfile = f'{name}-log.log'
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s %(process)d:%(thread)d %(name)s %(levelname)-8s %(message)s')

    stdouthandler = logging.StreamHandler(sys.stdout)
    stdouthandler.setLevel(logging.INFO)
    stdouthandler.setFormatter(formatter)
    log.addHandler(stdouthandler)

    rothandler = logging.handlers.RotatingFileHandler(logfile, maxBytes=8*1024, backupCount=3)
    rothandler.setLevel(logging.INFO)
    rothandler.setFormatter(formatter)
    log.addHandler(rothandler)

    return log

class WinPipeServer:
    def __init__(self, WorkerClass, logger):
        self._overlapped = pywintypes.OVERLAPPED()
        self._overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        self._hStop = win32event.CreateEvent(None, 0, 0, None)
        self._quit = False
        self._workerClass = WorkerClass
        self.log = logger
    
    def stop(self):
        self._quit = True
        win32event.SetEvent(self._hStop)
    
    def start(self):
        print('Server has started')
        while not self._quit:
            se_attrs = win32security.SECURITY_ATTRIBUTES()
            se_attrs.SECURITY_DESCRIPTOR.Initialize() # necessary?
            # DACL present, null DACL for world-accessible
            se_attrs.SECURITY_DESCRIPTOR.SetSecurityDescriptorDacl(True, None, False)
            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1, # 1 instance
                INBUF_SIZE,
                OUTBUF_SIZE,
                0,
                se_attrs
            )
            try:
                hr = win32pipe.ConnectNamedPipe(pipe, self._overlapped)
                if hr == winerror.ERROR_PIPE_CONNECTED:
                    win32event.SetEvent(self._overlapped.hEvent)
                self._wait_for_events(pipe)
            except win32pipe.error as e:
                code, source, message = e.args
                # TODO don't handle these errors just yet. need to figure out what to do here
                if code == winerror.ERROR_BROKEN_PIPE:
                    # client likely disconnected.
                    pass
                elif code == winerror.ERROR_PIPE_BUSY:
                    self.log.error('Pipe busy: is another instance of the server running?')
                    self.stop()
                else:
                    self.log.warn('unknown windows error:', e)
                    self.stop()
            except Exception as e:
                self.log.exception(f'Caught an exception: {e}')
                self.stop()
            except KeyboardInterrupt:
                print('Exiting...')
                self.stop()
            finally:
                win32file.CloseHandle(pipe)

    def _wait_for_events(self, pipe ,timeout = 1): # timeout in ms
        while not self._quit:
            rc = win32event.WaitForMultipleObjects((self._hStop, self._overlapped.hEvent), 0, timeout)
            if rc == win32event.WAIT_TIMEOUT:
                continue
            if rc == win32event.WAIT_FAILED:
                self.log.error('Failed to wait!')
                break

            index = rc - win32event.WAIT_OBJECT_0
            if index == 0: # stop signal
                self.stop()
                break
            elif index == 1: # data signal
                sock = WinPipeSock(pipe)
                worker = self._workerClass(sock, self.log)
                try:
                    worker.run()
                except WorkerError as e:
                    # TODO send error
                    self.log.error(f'Worker error: {e}')
                break

def main(logger):
    print('Starting...')
    # import takes a while
    from worker import ArgusWorker
    server = WinPipeServer(ArgusWorker, logger)
    server.start()

if __name__ == '__main__':
    log = setup_logger('server')

    if path.exists(LOCK_FILE):
        log.error(f'lock file "{LOCK_FILE}" exists. If server is not running, delete the file.')
        sys.exit(EXIT_FAILURE)

    try:
        # create lock file
        with open(LOCK_FILE, 'a'): pass
        main(log)
    except Exception as e:
        log.exception(f'Server failed with exception: {e}')
        sys.exit(EXIT_FAILURE)
    finally:
        if path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    sys.exit(EXIT_SUCCESS)