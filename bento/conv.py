from bento.core import \
        PackageDescription
from bento.core.utils import \
        InvalidPackage, validate_package as _validate_package
from bento.core.pkg_objects import \
        Executable

_PKG_TO_DIST = {
        "ext_modules": lambda pkg: [v for v  in \
                                    pkg.extensions.values()],
        "platforms": lambda pkg: [v for v  in pkg.platforms],
        "packages": lambda pkg: [v for v  in pkg.packages],
        "py_modules": lambda pkg: [v for v  in pkg.py_modules],
}

for k in ["name", "version", "summary", "url", "author",
          "author_email", "maintainer", "maintainer_email",
          "license", "description", "download_url"]:
    _PKG_TO_DIST[k] = lambda pkg: getattr(pkg, k)

def pkg_to_distutils(pkg):
    """Convert PackageDescription instance to a dict which may be used
    as argument to distutils/setuptools setup function."""
    d = {}

    for k, v in _PKG_TO_DIST.items():
        d[k] = v(pkg)

    return d

def validate_packages(pkgs):
    ret_pkgs = []
    for pkg in pkgs:
        try:
            _validate_package(pkg, ".")
        except InvalidPackage:
            # FIXME: add the package as data here
            pass
        else:
            ret_pkgs.append(pkg)
    return ret_pkgs

def distutils_to_package_description(dist):
    data = {}

    data['name'] = dist.get_name()
    data['version'] = dist.get_version()
    data['author'] = dist.get_author()
    data['author_email'] = dist.get_author_email()
    data['maintainer'] = dist.get_contact()
    data['maintainer_email'] = dist.get_contact_email()
    data['summary'] = dist.get_description()
    data['description'] = dist.get_long_description()
    data['license'] = dist.get_license()
    data['platforms'] = dist.get_platforms()

    data['download_url'] = dist.get_download_url()
    data['url'] = dist.get_url()

    # XXX: reliable way to detect whether Distribution was monkey-patched by
    # setuptools
    try:
        reqs = getattr(dist, "install_requires")
        # FIXME: how to detect this correctly
        if issubclass(type(reqs), (str, unicode)):
            reqs = [reqs]
        data['install_requires'] = reqs
    except AttributeError:
        pass

    data['py_modules'] = dist.py_modules
    data['packages'] = validate_packages(dist.packages)
    if dist.ext_modules:
        data['extensions'] = dict([(e.name, e) for e in dist.ext_modules])
    else:
        data['extensions'] = {}
    data['classifiers'] = dist.get_classifiers()

    data["executables"] = {}

    entry_points = entry_points_from_dist(dist)
    if entry_points:
        console_scripts = entry_points.get("console_scripts", [])
        for entry in console_scripts:
            exe = Executable.from_representation(entry)
            data["executables"][exe.name] = exe

    return PackageDescription(**data)

_DIST_CONV_DICT = {
    "long_description": lambda meta: meta.description,
    "description": lambda meta: meta.summary,
    # TODO: keywords not implemented yet
    "keywords": lambda meta: [],
    "fullname": lambda meta: "%s-%s" % (meta.name, meta.version),
    "contact": lambda meta: (meta.maintainer or
                             meta.author or
                             "UNKNOWN"),
    "contact_email": lambda meta: (meta.maintainer_email or
                                   meta.author_email or
                                   "UNKNOWN"),
    "requires": lambda meta: meta.install_requires
}

def to_distutils_meta(meta):
    from bento.compat.dist \
        import \
            DistributionMetadata
    ret = DistributionMetadata()
    for m in ret._METHOD_BASENAMES:
        try:
            val = _DIST_CONV_DICT[m](meta)
        except KeyError:
            val = getattr(meta, m)
        setattr(ret, m, val)

    return ret

def write_pkg_info(pkg, file):
    dist_meta = to_distutils_meta(pkg)
    dist_meta.write_pkg_file(file)

def entry_points_from_dist(dist):
    if hasattr(dist, "entry_points"):
        from pkg_resources import split_sections
        if isinstance(dist.entry_points, basestring):
            entry_points = {}
            sections = split_sections(dist.entry_points)
            for group, lines in sections:
                group = group.strip()
                entry_points[group] = lines
        else:
            entry_points = dist.entry_points
    else:
        entry_points = {}
    return entry_points
