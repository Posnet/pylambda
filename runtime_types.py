import ctypes
from ctypes import sizeof

PADDING = False
FOLLOW_POINTER = True

PREFIX = ''
PN = 4
P = PN * '_'
class PStruct(ctypes.Structure):
    _pack_ = 0x8
    _pwr = 0x2
    def __init__(self, *args, **kwargs):
       self._prefix = ''
       super().__init__(*args, **kwargs)
       
    def __str__(self):
        global PREFIX
        total = 0
        ret = '{\n'
        if hasattr(self, '_pack_'):
            PREFIX += P
        for n, t in self._fields_:
            val = getattr(self, n)
            if FOLLOW_POINTER:
                while hasattr(val, 'contents'):
                    val = val.contents
                 

                
            ret += f'{PREFIX}{hex(total)} {n}: {str(val)},\n'
            
            size = sizeof(t)
            total += size
            if PADDING:
               rem = total % self._pack_
               if total % self._pwr != 0:
                   padding = self._pack_ - rem
                   ret += f'{PREFIX}{hex(total)}  padding: {padding},\n'
                   total += padding
        ret = ret[:-2]
        if hasattr(self, '_pack_'):
            PREFIX = PREFIX[-PN:]
        ret += '}'

        return ret

class SharedMem(PStruct):
    _fields_ = [
        ('event_body_len', ctypes.c_int),
        ('debug_log_len', ctypes.c_int),
        ('event_body', ctypes.c_char * 6291556),
        ('debug_logs', ctypes.c_char * 102968),
        ('response_body_len', ctypes.c_int),
    ]
        
class timeval(PStruct):
    _fields_ = [
        ("tv_sec", ctypes.c_uint64),
        ("tv_usec", ctypes.c_uint64)
        ]
    
class XrayContext(PStruct):
    _fields_ = [
        ("trace_id", ctypes.c_char * 255),
        ("is_sampled", ctypes.c_bool),
        ("parent_id", ctypes.c_char * 255),
        ("lambda_id", ctypes.c_char * 255)
        ]
            
class AWSCredentials(PStruct):
    _fields_ = [
        ('key', ctypes.c_char * 128),
        ('secret', ctypes.c_char * 128),
        ('session', ctypes.c_char * 2048)
        ]
        
    def to_dict(self):
        return {key: getattr(self, key).decode('ascii')
                for key, typ in self._fields_}
            
class RequestStart(PStruct):
    
    _fields_ = [
        ("invoke_id", ctypes.c_char * 37),
        ("credentials", AWSCredentials),
        ("timeout_ms", ctypes.c_uint32),
        ("suppress_user_init_function", ctypes.c_bool),
        ("handler", ctypes.c_char * 128),
        # In the actual runtime this is an enum
        # event, http, none (0,1,2)
        # however the string is sent in the command
        # so it is easier just to keep it a string
        ("mode", ctypes.c_char * 10) 
        ]

class Runtime(PStruct):
    _fields_ = [
        ("ctrl_sock", ctypes.c_int),
        ("console_sock", ctypes.c_int),
        ("xray_sock", ctypes.c_int),
        ("needs_debug_logs", ctypes.c_int),
        ("function_arn", ctypes.c_char * 512),
        ("deadline_ns", ctypes.c_uint64),
        ("shared_mem", ctypes.POINTER(SharedMem)),
        ("pre_load_time_ns", ctypes.c_uint64),
        ("post_load_time_ns", ctypes.c_uint64),
        ("wait_start_time_ns", ctypes.c_uint64),
        ("wait_end_time_ns", ctypes.c_uint64),
        ("max_stall_time_ms", ctypes.c_size_t),
        ("is_initialized", ctypes.c_bool),
        ("init_start_time", timeval),
        ("init_end_time", timeval),
        ("invoke_start_time", timeval),
        ("is_traced", ctypes.c_bool),
        ("reported_xray_exception", ctypes.c_bool),
        ("init_xray_context", XrayContext),
        ("xray_context", XrayContext)
        ]