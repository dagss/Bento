import os
import sys
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import subprocess

from cPickle \
    import \
        dumps

from yaku.pprint \
    import \
        pprint
from yaku.errors \
    import \
        TaskRunFailure, WindowsError

# TODO:
#   - factory for tasks, so that tasks can be created from strings
#   instead of import (import not extensible)
class Task(object):
    def __init__(self, name, outputs, inputs, func=None, deps=None):
        if isinstance(inputs, basestring):
            self.inputs = [inputs]
        else:
            self.inputs = inputs
        if isinstance(outputs, basestring):
            self.outputs = [outputs]
        else:
            self.outputs = outputs
        self.name = name or ""
        self.uid = None
        self.func = func
        if deps is None:
            self.deps = []
        else:
            self.deps = deps
        self.cache = None
        self.env = None
        self.env_vars = None
        self.scan = None
        self.disable_output = False
        self.log = None

    # UID and signature functionalities
    #----------------------------------
    def get_uid(self):
        if self.uid is None:
            m = md5()
            up = m.update
            up(self.__class__.__name__.encode())
            for x in self.inputs + self.outputs:
                up(x.abspath().encode())
            self.uid = m.digest()
        return self.uid

    def signature(self):
        if self.cache is None:
            sig = self._signature()
            self.cache = sig
            return sig
        else:
            return self.cache

    def _signature(self):
        m = md5()

        self._sig_explicit_deps(m)
        for k in self.env_vars:
            m.update(dumps(self.env[k]))
        if self.func:
            m.update(self.func.func_code.co_code)
        return m.digest()

    def _sig_explicit_deps(self, m):
        for s in self.inputs + self.deps:
            #if os.path.exists(s):
            #    m.update(open(s).read())
            m.update(s.read(flags="rb"))
        return m.digest()
        
    # execution
    #----------
    def run(self):
        self.func(self)

    def exec_command(self, cmd, cwd):
        if cwd is None:
            cwd = self.gen.bld.bld_root.abspath()
        if not self.disable_output:
            if self.env["VERBOSE"]:
                pprint('GREEN', " ".join([str(c) for c in cmd]))
            else:
                pprint('GREEN', "%-16s%s" % (self.name.upper(), " ".join([i.bldpath() for i in self.inputs])))

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, cwd=cwd)
            stdout = p.communicate()[0].decode("utf-8")
            if p.returncode:
                raise TaskRunFailure(cmd, stdout)
            if self.disable_output:
                if sys.version_info >= (3,):
                    self.log.write(stdout)
                else:
                    self.log.write(stdout.encode("utf-8"))
            else:
                sys.stderr.write(stdout.encode("utf-8"))
        except OSError, e:
            raise TaskRunFailure(cmd, str(e))
        except WindowsError, e:
            raise TaskRunFailure(cmd, str(e))

    def __repr__(self):
        ins = ",".join([i.name for i in self.inputs])
        outs = ",".join([i.name for i in self.outputs])
        return "'%s: %s -> %s'" % (self.name, ins, outs)
