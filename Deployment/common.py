from enum import Enum
import string
import random
import time
from os import path
from contextlib import contextmanager
import win32file, winerror

MAX_SIZE = 2 * 1024 * 1024 * 1024 # 2 GB

PIPE_NAME = r'\\.\pipe\AnatomicRecon-POCUS-AI\inference-server'
LOCK_FILE = path.join(path.dirname(path.abspath(__file__)), 'argus.lock')
LOG_FILE = path.join(path.dirname(path.abspath(__file__)), 'server-log.log')

EXIT_FAILURE = 1
EXIT_SUCCESS = 0

def randstr(length):
    size = len(string.ascii_letters)
    return ''.join(string.ascii_letters[random.randint(0, size-1)] for _ in range(length))

class WorkerError(Exception):
    pass

class Message:
    # message type is a single byte
    class Type(Enum):
        # messages from cli
        START = 0x1
        # messages from server
        RESULT = 0x81
        ERROR = 0x82

        def tobyte(self):
            return self.value.to_bytes(1, 'big')
        
        @classmethod
        def frombyte(cls, byte):
            return cls(int.from_bytes(byte, 'big'))

    def __init__(self, mtype, data):
        '''mtype can either be an integer or a Message.Type'''
        self.type = Message.Type(mtype)
        self.data = data
    
    def tobytes(self):
        return self.type.tobyte() + self.data
    
    @classmethod
    def parse_bytes(cls, data):
        return cls(Message.Type.frombyte(data[:1]), data[1:])

class Stats:

    def __init__(self):
        self.timers = dict()
        self._running_timers = dict()
        self._global_start = time.time()

    def time_start(self, name):
        start = time.time() - self._global_start
        self._running_timers[name] = start

    def time_end(self, name):
        end = time.time() - self._global_start
        if name in self._running_timers:
            self.timers[name] = dict(
                start=self._running_timers[name],
                end=end,
                elapsed=end - self._running_timers[name]
            )
            del self._running_timers[name]
    
    @contextmanager
    def time(self, name):
        self.time_start(name)
        yield
        self.time_end(name)
    
    def todict(self):
        return dict(timers=self.timers)

class Sock:
    def recv(self):
        raise NotImplementedError()
    def send(self, data):
        raise NotImplementedError()

class WinPipeSock(Sock):
    def __init__(self, pipe):
        self._pipe = pipe

    def recv(self):
        chunk_size = 64 * 1024
        data = bytearray()
        hr = winerror.ERROR_MORE_DATA
        size = 0
        while hr == winerror.ERROR_MORE_DATA:
            # TODO handle blocking scenario?
            hr, chunk = win32file.ReadFile(self._pipe, chunk_size)
            size += len(chunk)
            if size > MAX_SIZE:
                raise Exception('Exceeded single message max size')
            data.extend(chunk)
        return Message.parse_bytes(bytes(data))
    
    def send(self, msg):
        win32file.WriteFile(self._pipe, msg.tobytes())