import ctypes
from runtime_types import *


def handler(event, context):
    rt_pointer = ctypes.POINTER(Runtime)
    l = ctypes.cdll.LoadLibrary('/var/runtime/awslambda/runtime.cpython-36m-x86_64-linux-gnu.so')
    rt = rt_pointer.in_dll(l, '__runtime')
    print(rt.contents)
    
    return "Failed to inject"
    
