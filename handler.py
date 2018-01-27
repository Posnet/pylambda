import ctypes
import sys
from inject.runtime_types import *


def handler(event, context):

    print(sys.path)
    print(get_native_runtime_struct())
    
    return "Failed to inject"
    
