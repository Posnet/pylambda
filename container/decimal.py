import sys
import os
import fcntl
# from inject.pyruntime import main
# from inject.bootstrap import main

# Reset FD_CLOEXEC flags for all FDs, before we execve our own runtime
for fd in list(os.walk("/proc/self/fd/"))[0][2]:
    fd = int(fd)
    if fcntl.fcntl(int(fd), fcntl.F_GETFD):
        fcntl.fcntl(fd, fcntl.F_SETFD, 0)

cmd = ["/var/lang/bin/python3.6", "/var/task/inject/bootstrap.py"]
os.execve(cmd[0], cmd, os.environ)

# main()

print('Failed to execve')
sys.exit(1)
