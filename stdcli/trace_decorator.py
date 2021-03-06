# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:textwidth=0:
# License: GPL2 or later see COPYING
# Written by Michael Brown
# Copyright (C) 2007 Michael E Brown <mebrown@michaels-house.net>

import logging
import os
import sys
import types


import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# use python-decoratortools if it is installed, otherwise use our own local
# copy. Imported this locally because it doesnt appear to be available on SUSE
# and the fedora RPM doesnt appear to compile cleanly on SUSE
try:
    from peak.util.decorators import rewrap, decorate
except ImportError:
    from peak_util_decorators import rewrap, decorate


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

#initialize this late because if it get initialized but unused we throw an exception on exit
null_handler = None

def format_function_call(func_name, *args, **kw):
    return  "%s(%s)" % (func_name,
                    ", ".join([repr(i) for i in args] + ["%s=%s" % (key, repr(value)) for key, value in kw.items()])
                    )

# defaults to module log
# does a late binding on log. Forwards all attributes to logger.
# works around problem where reconfiguring the logging module means loggers
# configured before reconfig dont output.
class getLog(object):
    def __init__(self, name=None, prefix="", *args, **kargs):
        # name the log per the module name if not supplied
        if name is None:
            frame = sys._getframe(1)
            name = frame.f_globals["__name__"]
        object.__setattr__(self, "name", prefix + name)

    # forward all attribute access to the logger
    def __getattr__(self, name):
        # get logger her so it gets instantiated as late as possible
        logger = logging.getLogger(self.name)
        global null_handler
        if null_handler is None:
            null_handler = NullHandler()
        # add null handlers so we can suppress usless "no handlers could be found for..." messages
        if not null_handler in logger.handlers:
            logger.addHandler(null_handler)
        return getattr( logger, name )

    # forward all attribute access to the logger
    def __setattr__(self, name, value):
        # get logger her so it gets instantiated as late as possible
        logger = logging.getLogger(self.name)
        global null_handler
        if null_handler is None:
            null_handler = NullHandler()
        # add null handlers so we can suppress usless "no handlers could be found for..." messages
        if not null_handler in logger.handlers:
            logger.addHandler(null_handler)
        return setattr( logger, name, value )


# emulates logic in logging module to ensure we only log
# messages that logger is enabled to produce.
def doLog(logger, level, *args, **kargs):
    if logger.manager.disable >= level:
        return
    if logger.isEnabledFor(level):
        try:
            logger.handle(logger.makeRecord(logger.name, level, *args, **kargs))
        except TypeError:
            del(kargs["func"])
            logger.handle(logger.makeRecord(logger.name, level, *args, **kargs))

def traceLog(log = None):
    def decorator(func):
        def trace(*args, **kw):
            # default to logger that was passed by module, but
            # can override by passing logger=foo as function parameter.
            # make sure this doesnt conflict with one of the parameters
            # you are expecting

            filename = os.path.normcase(func.func_code.co_filename)
            func_name = func.func_code.co_name
            lineno = func.func_code.co_firstlineno

            l2 = kw.get('logger', log)
            if l2 is None:
                l2 = getLog("trace.%s" % func.__module__)
            if isinstance(l2, basestring):
                l2 = getLog(l2)

            message = "ENTER %s" % format_function_call(func_name, *args, **kw)

            frame = sys._getframe(2)
            doLog(l2, logging.INFO, os.path.normcase(frame.f_code.co_filename), frame.f_lineno, message, args=[], exc_info=None, func=frame.f_code.co_name)
            try:
                result = "Bad exception raised: Exception was not a derived class of 'Exception'"
                try:
                    result = func(*args, **kw)
                except (SystemExit, KeyboardInterrupt), e:
                    result = "SYSTEM EXIT or KEYBOARD INTERRUPT: %s" % e.__class__
                    # only print stack trace once when we catch this
                    if not hasattr(e, "already_printed"):
                        doLog(l2, logging.INFO, filename, lineno, "SYSTEM EXIT or KEYBOARD INTERRUPT: %s\n" % e, args=[], exc_info=sys.exc_info(), func=func_name)
                        e.already_printed = 1
                    raise
                except (Exception), e:
                    result = "EXCEPTION RAISED: %s" % e.__class__
                    if not hasattr(e, "already_printed"):
                        doLog(l2, logging.INFO, filename, lineno, "EXCEPTION: %s\n" % e, args=[], exc_info=sys.exc_info(), func=func_name)
                        e.already_printed = 1
                    raise
            finally:
                doLog(l2, logging.INFO, filename, lineno, "LEAVE %s --> %s\n" % (func_name, repr(result)), args=[], exc_info=None, func=func_name)

            return result
        return rewrap(func, trace)
    return decorator

# helper function so we can use back-compat format but not be ugly
def decorateAllFunctions(module, logger=None):
    methods = [ method for method in dir(module)
            if isinstance(getattr(module, method), types.FunctionType)
            ]
    for i in methods:
        setattr(module, i, traceLog(logger)(getattr(module,i)))

# unit tests...
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                    format='%(name)s %(levelname)s %(filename)s, %(funcName)s, Line: %(lineno)d:  %(message)s',)
    log = getLog("foobar.bubble")
    root = getLog(name="")
    log.setLevel(logging.WARNING)
    root.setLevel(logging.DEBUG)

    log.debug(" --> debug")
    log.error(" --> error")

    decorate(traceLog(log))
    def testFunc(arg1, arg2="default", *args, **kargs):
        return 42

    testFunc("hello", "world", logger=root)
    testFunc("happy", "joy", name="skippy")
    testFunc("hi")

    decorate(traceLog(root))
    def testFunc22():
        return testFunc("archie", "bunker")

    testFunc22()

    decorate(traceLog(root))
    def testGen():
        yield 1
        yield 2

    for i in testGen():
        log.debug("got: %s" % i)

    decorate(traceLog())
    def anotherFunc(*args):
        return testFunc(*args)

    anotherFunc("pretty")

    getLog()
