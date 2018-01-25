import os
from os import environ
import time
import sys
import fcntl
import logging
import mmap
import ctypes
from ctypes import sizeof, addressof
from subprocess import check_output
from runtime_types import *

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
RUNTIME = None
CLEANUP = not DEBUG
FUNCTION_NAME = ""
LOG_SINK = None
LOG_CONTEXT = ""
SEND_INIT_SUBSEGMENT_CALL_COUNT = 0
# ---------------------------------------------------------------------------- #


# RUNTIME FUNCTION ----------------------------------------------------------- #
def parse_x_amzn_trace_id(trace_id):
    logger.debug(f'trace_id: "{trace_id}"')
    
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

def log_sb(msg)
    lambda_logf(True, "%s\n", msg)
    
def get_time_of_day_millis():
    return int(time.time() * 1000)
    
def get_pretty_time(is_iso=False):
    t = time.time()
    t_struct = time.gmtime(t)
    millis = round((t - int(t)) * 1000)
    if is_iso:
        text = time.strftime('%FT%T', t_struct)
        fmt  = '%s.%03ldZ'
    else:
        text = time.strftime('%d %b %Y %H:%M:%S', t_struct)
        fmt  =  '%s,%03ldZ' 
        
    return fmt % (text, millis)
        
def lambda_logf(profile, format_string, *args):
    
    if profile:
        start = get_time_of_day_millis()
        
    if not LOG_SINK:
        sink = sys.stderr

    sink.write(get_pretty_time(False))
    if LOG_CONTEXT:
        sink.write(f'{{{LOG_CONTEXT}}}')
    sink.write(format_string % args)
    
    if profile:
        duration = get_time_of_day_millis - start
        if duration > 100:
            lambda_logf(False, "[WARN] logging previous line took %llums\n", duration)
        
def runtime_init():
    runtime = Runtime()
    
    FUNCTION_NAME = environ['AWS_LAMBDA_FUNCTION_NAME']
    LOG_CONTEXT = f"sandbox:{environ['_LAMBDA_SB_ID']}"
    log_sink_fd = int(environ['_LAMBDA_LOG_FD'])
    LOG_SINK = open(log_sink_fd,
                    mode='wb',
                    buffering=0,
                    opener=lambda x: os.open(x, os.O_APPEND))
    
    
    runtime.ctrl_sock = int(environ['_LAMBDA_CONTROL_SOCKET'])
    runtime.console_sock = int(environ['_LAMBDA_CONSOLE_SOCKET'])
    
    init_context = parse_x_amzn_trace_id(environ['_X_AMZN_TRACE_ID'])
    runtime.init_xray_context = init_context
    
    
    shm_fd = int(environ['_LAMBDA_SHARED_MEM_FD'])
    shm = mmap.mmap(shm_fd,
                    length=sizeof(SharedMem),
                    flags=mmap.MAP_SHARED,
                    prot=mmap.PROT_READ | mmap.PROT_WRITE)
    runtime.shared_mem = ctypes.pointer(SharedMem.from_buffer(shm))
    
    if DEBUG:
        out = check_output(['cat', '/proc/1/maps'])
        out = out.decode('ascii')
        out = out.split('\n')
        logger.debug([i for i in out if 'shm' in i][0])

    # TODO Xray socket
    # socket(2, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0)
    # addr = environ["_AWS_XRAY_DAEMON_ADDRESS"]
    # port = environ["_AWS_XRAY_DAEMON_PORT"]
    runtime.xray_sock = -1
    
    runtime.is_traced = False
    runtime.is_initialized = False
    runtime.needs_debug_logs = False
    runtime.max_stall_time_ms = 0
    runtime.pre_load_time_ns = int(environ['_LAMBDA_RUNTIME_LOAD_TIME'])
    runtime.post_load_time_ns = int(time.clock_gettime(
                                    time.CLOCK_MONOTONIC) * 10 ** 9)
    
    if CLEANUP:
        del environ['_LAMBDA_LOG_FD']
        del environ['_LAMBDA_SB_ID']
        del environ['_LAMBDA_CONTROL_SOCKET']
        del environ['_LAMBDA_CONSOLE_SOCKET']
        del environ['_LAMBDA_SHARED_MEM_FD']
        del environ['_LAMBDA_RUNTIME_LOAD_TIME']
        os.close(shm_fd)
        
    logger.debug(runtime)
    
    return runtime
# ---------------------------------------------------------------------------- #


# ENTRYPOINT ----------------------------------------------------------------- #
def main():
    logger.info('Start of Boostrap')
    try:
        RUNTIME = runtime_init()
    except Exception as e:
        print('ERROR')
        logger.exception(e)
        pass
    logger.info('End of Boostrap')    
# ---------------------------------------------------------------------------- #




#### RUNTIME STUFF ###
#     
#     l = ctypes.cdll.LoadLibrary('/var/runtime/awslambda/runtime.cpython-36m-x86_64-linux-gnu.so')
#     rt = rt_pointer.in_dll(l, '__runtime')


#  # f = open('/dev/shm/sandbox2753_eventbody111')
#     # mm = mmap.mmap(f.fileno(), 100)
    
#     # with open("/proc/1/maps", 'r') as f:
#         # for _ in range(15):
#             # print(f.readline().strip())
    
    
   
    
    
    
#     print(rt.contents.pre_load_time_ns)
#     print(rt.contents.post_load_time_ns)
    
#     with open('/proc/1/environ') as f:
#         print(f.read().split('\0'))
#     # shared_mem = rt.contents.shared_mem.contents
#     # print(str(shared_mem))
#     # print()
#     # # print(shared_mem.event_body, shared_mem.event_body_len)
#     # res = b'{"test":"result"}'
#     # res_len = len(res)
#     # shared_mem.event_body = res
#     # shared_mem.response_body_len = ctypes.c_int(res_len)
#     # # print(shared_mem.event_body)
#     # print(str(shared_mem))
#     # print()
#     # print(l.runtime_report_done(rt, ctypes.c_char_p(bytes(context.aws_request_id, 'ascii')), None, False))
#     # print('after done')
#     # print()
#     # print(str(shared_mem))

    
#     # sys.exit(0)
    
    
#     # import runtime
#     # runtime.log_bytes(b"to 1", 1)
#     # runtime.log_bytes(b"to 2", 2)
#     # runtime.log_bytes(b"to 3", 3)
#     # runtime.log_bytes(b"to 20", 20)
    
#     # print(context.__dict__)
#     # runtime.report_user_invoke_end()
#     # runtime.report_done(context.aws_request_id, None, '{"test":"result"}')
#     # sys.exit()
#     # print(check_output('cat /proc/1/mountinfo', shell=True).decode('ascii'))
#     # context.log('test')
#     # print(sys.stdin)
#     # print(sys.stdout)
#     # print(sys.stderr)
#     # print(inspect.stack())
#     # for fd in range(50):
#     #     try:
#     #         # print(f"{fd}: {fcntl.fcntl(fd, fcntl.F_GETFD)}")
#     #         fcntl.fcntl(fd, fcntl.F_SETFD, 0)
#     #         print(f"{fd}: {fcntl.fcntl(fd, fcntl.F_GETFD)}")
#     #     except:
#     #         pass
        
#     # os.execv('/var/task/thing.py', [''])
#     # runtime.send_console_message("before exec")
#     # try:
#     #     # print(check_output("/var/lang/bin/python3.6 /var/task/lambda_function.py",  stderr=subprocess.STDOUT, shell=True).decode("ascii"))
#     #     # print(check_output("/var/lang/bin/python3.6 --version", shell=True).decode("ascii"))
#     #     cmd = f"/var/lang/bin/python3.6 /var/task/lambda_function.py"
        
#     #     p = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     #     out = p.stdout.decode('ascii')
#     #     err = p.stderr.decode('ascii')
#     #     ret = err + "\n" + out
#     #     ret =  ret.encode('ascii')
#     #     print(ret)
#     # except:
#     #     logger.exception('fail')
    
#     # print(rt)
#     # return 
#     # size = 6500
#     # mem_struct = ctypes.string_at(rt.contents.shared_mem, size)
#     # s3 = boto3.client('s3')
#     # s3.put_object(Bucket='my-p-good-bucket', Key='memdump', Body=mem_struct)
    
#     # return
    
#     # print(hex(ctypes.c_void_p.from_buffer(rt.contents.shared_mem).value))
#     # print(rt.contents.deadline)
#     # res = ctypes.cast(addr, ctypes.POINTER(SharedMem)).contents
    
#     # print(os.execve("/var/lang/bin/python3.6", ["/var/task/lambda_function.py", context.aws_request_id], os.environ))


