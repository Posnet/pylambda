import ctypes
from runtime_types import *


def handler(event, context):

    print(get_native_runtime_struct())
    
    return "Failed to inject"
    
