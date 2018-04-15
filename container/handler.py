import sys
from inject.runtime_types import get_native_runtime_struct


def pyhandler(event, context):
    print(event, context)
    return {'working': True}


def handler(event, context):

    print(sys.path)
    print(get_native_runtime_struct())

    return "Failed to inject"
