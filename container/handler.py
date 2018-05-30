import sys
import subprocess
from inject.runtime_types import get_native_runtime_struct


def pyhandler(event, context):
    print(event, context)
    out = str(subprocess.check_output(['ps', '1'])).split('\\n')[1]
    return {'working': True, 'current_proc': out}


def handler(event, context):

    print(sys.path)
    print(get_native_runtime_struct())

    return "Failed to inject"
