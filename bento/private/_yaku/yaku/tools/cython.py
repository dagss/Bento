import os
import sys

from yaku.task_manager \
    import \
        extension, get_extension_hook
from yaku.task \
    import \
        Task
from yaku.compiled_fun \
    import \
        compile_fun
from yaku.utils \
    import \
        ensure_dir, find_program
import yaku.errors

@extension(".pyx")
def cython_hook(self, node):
    self.sources.append(node.change_ext(".c"))
    return cython_task(self, node)

def cython_task(self, node):
    out = node.change_ext(".c")
    target = node.parent.declare(out.name)
    ensure_dir(target.name)

    task = Task("cython", inputs=[node], outputs=[target])
    task.gen = self
    task.env_vars = []
    task.env = self.env

    self.env["CYTHON_INCPATH"] = ["-I%s" % p for p in
                self.env["CYTHON_CPPPATH"]]
    task.func = compile_fun("cython", "${CYTHON} ${SRC} -o ${TGT} ${CYTHON_INCPATH}",
                            False)[0]
    return [task]

def configure(ctx):
    sys.stderr.write("Looking for cython... ")
    if detect(ctx):
        sys.stderr.write("yes\n")
    else:
        sys.stderr.write("no!\n")
        raise yaku.errors.ToolNotFound()
    ctx.env["CYTHON_CPPPATH"] = []
    ctx.env["CYTHON"] = [sys.executable, "-m", "cython"]

def detect(ctx):
    if find_program("cython") is None:
        return False
    else:
        return True
