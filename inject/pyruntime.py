import os
import time
import sys
import fcntl
import logging
import mmap
import ctypes
import socket
import array
import struct
from .fromfd import fromfd
from ctypes import sizeof, addressof
from subprocess import check_output
from os import environ
from .runtime_types import *

# LOGGING -------------------------------------------------------------------- #
# LAMBDA_LOG_FORMAT = \
# "[%(levelname)s]\t%(asctime)s.%(msecs)dZ\t%(aws_request_id)s\t%(message)s\n"
LOG_FORMAT = "[%(levelname)8s]\t%(message)s\t(%(filename)s:%(lineno)s)"
LOG_LEVEL = environ['LOG_LEVEL']
DEBUG = LOG_LEVEL == 'DEBUG'
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
# ---------------------------------------------------------------------------- #


# RUNTIME GLOBALS ------------------------------------------------------------ #
CLEANUP = not DEBUG

# ---------------------------------------------------------------------------- #


# MISC FUNCTIONS  ------------------------------------------------------------ #
def recv_fds(sock, msglen, maxfds):
    fds = array.array("i")   # Array of ints
    size = socket.CMSG_LEN(maxfds * fds.itemsize)
    msg, ancdata, flags, addr = sock.recvmsg(msglen, size)
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if (cmsg_level == socket.SOL_SOCKET \
        and cmsg_type == socket.SCM_RIGHTS):
            # Append data, ignoring any truncated integers at the end.
            data = cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)]
            fds.fromstring(data)
    return msg, list(fds)
    
def parse_x_amzn_trace_id(trace_id):
    # logger.debug(f'trace_id: "{trace_id}"')
    
    ctx = XrayContext()
    kvs =  { x[0]: x[1].encode('ascii') 
            for x in
            [y.split('=') for y in  trace_id.split(';')]
           }
    
    ctx.lambda_id = b''
    ctx.trace_id = kvs.get('Root', b'')
    ctx.parent_id = kvs.get('Parent', b'')
    ctx.is_sampled = True if kvs.get('is_sampled', b'0') == '1' else False
    
    return ctx
    
def parse_kv_msg(msg, decode=False):
    msgs = msg.split(b'\x00')[:-1] 
    msgs = [msg.decode('ascii') if decode else msg for msg in msgs ]
    return dict(zip(msgs[::2], msgs[1::2]))
    
    
def clock_gettime_ns():
    return int((10 ** 9) * time.clock_gettime(time.CLOCK_MONOTONIC))
    
    
def get_time_of_day_millis():
    return int(time.time() * 1000)
    
    
def get_pretty_time(is_iso=False):
    t = time.time()
    t_struct = time.gmtime(t)
    millis = round((t - int(t)) * 1000)
    if is_iso:
        text = time.strftime('%FT%T', t_struct)
        fmt  = '{}.{:03d}Z'
    else:
        text = time.strftime('%d %b %Y %H:%M:%S', t_struct)
        fmt  =  '{},{:03d}Z' 

# ---------------------------------------------------------------------------- #


# RUNTIME CLASS -------------------------------------------------------------- #
class PyRuntime:
    COMMAND_MAGIC = bytes([71,105,114,68])
    
    def __init__(self):
        runtime = Runtime()
        
        self.SEND_INIT_SUBSEGMENT_CALL_COUNT = 0
        self.FUNCTION_NAME = environ['AWS_LAMBDA_FUNCTION_NAME']
        self.LOG_CONTEXT = f"sandbox:{environ['_LAMBDA_SB_ID']}"
        
        log_sink_fd = int(environ['_LAMBDA_LOG_FD'])
        self.LOG_SINK = open(log_sink_fd,
                        mode='wb',
                        buffering=0,
                        opener=lambda x: os.open(x, os.O_APPEND))
        
        
        runtime.ctrl_sock = int(environ['_LAMBDA_CONTROL_SOCKET'])
        self.ctrl_sock = fromfd(runtime.ctrl_sock)
        
        runtime.console_sock = int(environ['_LAMBDA_CONSOLE_SOCKET'])
        self.console_sock = fromfd(runtime.console_sock)
        
        init_context = parse_x_amzn_trace_id(environ['_X_AMZN_TRACE_ID'])
        runtime.init_xray_context = init_context
        
        
        shm_fd = int(environ['_LAMBDA_SHARED_MEM_FD'])
        shm = mmap.mmap(shm_fd,
                        length=sizeof(SharedMem),
                        flags=mmap.MAP_SHARED,
                        prot=mmap.PROT_READ | mmap.PROT_WRITE)
        runtime.shared_mem = ctypes.pointer(SharedMem.from_buffer(shm))
        
        # if DEBUG:
        #     out = check_output(['cat', '/proc/1/maps'])
        #     out = out.decode('ascii')
        #     out = out.split('\n')
        #     logger.debug([i for i in out if 'shm' in i][0])
    
        # TODO Xray socket
        # socket(2, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0)
        # addr = environ["_AWS_XRAY_DAEMON_ADDRESS"]
        # port = environ["_AWS_XRAY_DAEMON_PORT"]
        runtime.xray_sock = -1
        self.xray_sock = -1
        
        runtime.is_traced = False
        runtime.is_initialized = False
        runtime.needs_debug_logs = False
        runtime.max_stall_time_ms = 0
        runtime.pre_load_time_ns = int(environ['_LAMBDA_RUNTIME_LOAD_TIME'])
        runtime.post_load_time_ns = clock_gettime_ns()
        
        if CLEANUP:
            del environ['_LAMBDA_LOG_FD']
            del environ['_LAMBDA_SB_ID']
            del environ['_LAMBDA_CONTROL_SOCKET']
            del environ['_LAMBDA_CONSOLE_SOCKET']
            del environ['_LAMBDA_SHARED_MEM_FD']
            del environ['_LAMBDA_RUNTIME_LOAD_TIME']
            os.close(shm_fd)
            
        # logger.debug(runtime)
        self._runtime = runtime
        
    def log_bytes(self, msg, fd):
        pass
        
    def log_sb(self, msg):
        self.lambda_logf(True, "{}\n", msg)
        return fmt.format(text, millis)
        
        
    def lambda_logf(profile, format_string, *args):
        
        if profile:
            start = get_time_of_day_millis()
            
        if not LOG_SINK:
            sink = sys.stderr
    
        sink.write(f"{get_pretty_time(False)} ")
        if LOG_CONTEXT:
            sink.write(f' {{{LOG_CONTEXT}}} ')
        sink.write(format_string.format(*args))
        
        if profile:
            duration = get_time_of_day_millis() - start
            if duration > 100:
                lambda_logf(False,
                "[WARN] logging previous line took {}ms\n", duration)
            
    def send_command(self, socket, command, kv_dict):
        body = b''
        for k, v in kv_dict.items():
            body += (str(k) + '\x00').encode('ascii')
            body += (str(v) + '\x00').encode('ascii')
    
        header = self.COMMAND_MAGIC
        header += struct.pack('>I', len(body))
        header += command.ljust(8, '\x00').encode('ascii')
        
        msg = header + body
        # logger.debug('command to send: %s', msg)
        socket.sendmsg([msg], [])
    
    
    def receive_command(self):
        msg, fds = recv_fds(self.ctrl_sock, 4096, 10)
        
        header, body = msg[:16], msg[16:]
        magic = header[:4]
        length = struct.unpack('>I', header[4:8])[0]
        
        assert magic == self.COMMAND_MAGIC
        assert length == len(body)
        
        command = header[8:].split(b'\x00')[0].decode('ascii')
    
        return command, body
    
    def receive_start(self):
        self._runtime.wait_start_time_ns = clock_gettime_ns()
        
        start_request = RequestStart()
        
        command, body = self.receive_command()
        kvs = parse_kv_msg(body)
        
        # logger.debug(kvs)
        
        assert command == 'START'
        
        credentials = AWSCredentials()
        credentials.key = kvs[b'awskey']
        credentials.secret = kvs[b'awssecret']
        credentials.session = kvs[b'awssession']
        
        start_request.suppress_user_init_function = kvs.get(b'supressinit', None)
        start_request.invoke_id = kvs[b'invokeid']
        start_request.mode = kvs[b'mode']
        start_request.handler = kvs[b'handler']
        start_request.credentials = credentials
        
        self.start_request = start_request
        
        self.LAMBDA_TASK_ROOT = environ['LAMBDA_TASK_ROOT']
        os.chdir(self.LAMBDA_TASK_ROOT)
        
        self._runtime.wait_end_time_ns = clock_gettime_ns()
        
        return (start_request.invoke_id.decode('ascii'),
                start_request.mode.decode('ascii'),
                start_request.handler.decode('ascii'),
                start_request.suppress_user_init_function,
                start_request.credentials.to_dict())
                
    def report_running(self, invoke_id):
        #  lambda_logf(1,
        #             "[INFO] (%s@%s:%d) (invokeid=%s) report running\n",
        #             "runtime_report_running",
        #             "src/lambda/runtime.c",
        #             573,
        #             invokeid)
        
        running_msg_dict = {
            'RUNTIME_PRELOAD_TIME_NS': str(self._runtime.pre_load_time_ns),
            'RUNTIME_POSTLOAD_TIME_NS': str(self._runtime.post_load_time_ns),
            'RUNTIME_WAIT_START_TIME_NS': str(self._runtime.wait_start_time_ns),
            'RUNTIME_WAIT_END_TIME_NS': str(self._runtime.wait_end_time_ns)
        }
        # logger.debug('running message: %s', running_msg_dict)
        self.send_command(self.ctrl_sock, 'RUNNING', running_msg_dict)
        
    def report_user_init_start(self):
        self._runtime.init_start_time = timeval.from_time(time.time())
        
        
    def report_user_init_end(self):
        self._runtime.init_end_time = timeval.from_time(time.time())
        
        
    def report_user_invoke_start(self):
        # TODO: if we are traced with xray, we need to send subsegments
        self._runtime.is_initialized = True
        
        
    def report_user_invoke_end(self):
        # TODO: if we are traced with xray, we need to send subsegments
        pass
    
    
    def get_remaining_time(self):
        pass
    
    
    def send_console_message(self):
        pass
    
    def report_fault(self):
        pass
    
    def receive_invoke(self):
        # note to self, this is where needs_debug_logs is set
        command, body = self.receive_command()
        kvs = parse_kv_msg(body)
        return command, kvs
        return (command, )
        pass
        # return (
        # invokeid,
        # data_sock,
        # credentials,
        # event_body,
        # context_objs,
        # invoked_function_arn,
        # x_amzn_trace_id
        # )
    
    def report_done(self, invokeid, errortype, result):
        # TODO write output to shared buffer
        
        command = 'DONE'
        kv_dict = {'errortype': errortype or '',
        'SBLOG:MaxStallTimeMs': self._runtime.max_stall_time_ms or 0,
        'wait_for_exit': 0}
        
        self.send_command(self.ctrl_sock, command, kv_dict)
        
    
# ---------------------------------------------------------------------------- #


# ENTRYPOINT ----------------------------------------------------------------- #
def main():
    logger.info('Start of Boostrap')
    try:
        runtime = PyRuntime()
        start = runtime.receive_start()
        logger.debug(start)
        runtime.report_running(start[0])
        runtime.report_done(start[0], None, None)
        logger.warn('after report running')
        cnt = 0
        
        while True:
            cnt += 1
            logger.info('invoke: %s', cnt)
            invoke = runtime.receive_invoke()
            logger.warn(invoke)
            
            logger.debug(runtime._runtime.shared_mem.contents)
            rsp = b'{"123": "123"}'
            runtime._runtime.shared_mem.contents.event_body = rsp
            runtime._runtime.shared_mem.contents.response_body_len = len(rsp)
            runtime._runtime.shared_mem.contents.event_body_len = 0
            logger.debug(runtime._runtime.shared_mem.contents)
            runtime.report_done('', None, None)
            
    except Exception as e:
        print('ERROR')
        logger.exception(e)
        pass
    logger.info('End of Boostrap')    
# ---------------------------------------------------------------------------- #
