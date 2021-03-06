import os

from bento.private.bytecode import \
        bcompile
from bento.core.utils import \
        pprint, ensure_dir
from bento.core import \
        PackageMetadata
from bento.installed_package_description import \
        InstalledPkgDescription, iter_files
from bento._config \
    import \
        IPKG_PATH

from bento.commands.errors \
    import \
        UsageException
from bento.commands.core import \
        Command, SCRIPT_NAME
from bento.commands.egg_utils import \
        EggInfo, egg_filename

import bento.compat.api as compat

class BuildEggCommand(Command):
    long_descr = """\
Purpose: build egg
Usage:   bentomaker build_egg [OPTIONS]"""
    short_descr = "build egg."

    def run(self, ctx):
        opts = ctx.cmd_opts
        o, a = self.parser.parse_args(opts)
        if o.help:
            self.parser.print_help()
            return

        if not os.path.exists(IPKG_PATH):
            raise UsageException("%s: error: %s subcommand require executed build" \
                    % (SCRIPT_NAME, "build_egg"))

        ipkg = InstalledPkgDescription.from_file(IPKG_PATH)
        build_egg(ipkg)

def build_egg(ipkg, source_root=".", path=None):
    meta = PackageMetadata.from_ipkg(ipkg)
    egg_info = EggInfo.from_ipkg(ipkg)

    # FIXME: fix egg name
    if path is None:
        egg = egg_filename(os.path.join("dist", meta.fullname))
    else:
        egg = egg_filename(os.path.join(path, meta.fullname))
    ensure_dir(egg)

    egg_info = EggInfo.from_ipkg(ipkg)

    zid = compat.ZipFile(egg, "w", compat.ZIP_DEFLATED)
    try:
        for filename, cnt in egg_info.iter_meta():
            zid.writestr(os.path.join("EGG-INFO", filename), cnt)

        ipkg.path_variables["sitedir"] = "."
        file_sections = ipkg.resolve_paths(source_root)
        for kind, source, target in iter_files(file_sections):
            if not kind in ["executables"]:
                zid.write(source, target)

        pprint("PINK", "Byte-compiling ...")
        for kind, source, target in iter_files(file_sections):
            if kind in ["pythonfiles"]:
                zid.writestr("%sc" % target, bcompile(source))
    finally:
        zid.close()

    return
