# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:tw=0

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""module

some docs here eventually.
"""

from __future__ import generators

import sys
import time
import subprocess

from trace_decorator import decorate, traceLog, getLog

def clearLine():
    return "\033[2K\033[0G"

def spinner(cycle=['/', '-', '\\', '|']):
    step = cycle[0]
    del cycle[0]
    cycle.append(step)
    # ESC codes for clear line and position cursor at horizontal pos 0
    return step

def pad(strn, pad_width=67):
    # truncate strn to pad_width so spinPrint does not scroll
    if len(strn) > pad_width:
        return strn[:pad_width] + ' ...'
    else:
        return strn

def spinPrint(strn, outFd=sys.stderr):
    outFd.write(clearLine())
    outFd.write("%s\t%s" % (spinner(), pad(strn)))
    outFd.flush()

def timedSpinPrint( strn, start ):
    now = time.time()
    # ESC codes for position cursor at horizontal pos 65
    spinPrint( strn + "\033[65G time: %2.2f" % (now - start) )

class CalledProcessError(Exception):
    def __init__(self, returncode, cmd, stdout=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d.\n\tstdout: %s\n\tstderr: %s" % (self.cmd, self.returncode, self.stdout, self.stderr)

@traceLog()
def call_output(cmd, *args, **kargs):
    raise_exc = kargs.get("raise_exc",True)
    if kargs.has_key("raise_exc"): del(kargs["raise_exc"])
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, *args, **kargs)
    output, err = process.communicate()
    retcode = process.poll()
    if retcode and raise_exc:
        raise CalledProcessError(retcode, cmd, stdout=output, stderr=err)
    return output

