"""
Cache version 1

db["version"] : version number
db["magic"]   : "BENTOMAGIC"
db["bento_checkums"] : pickled dictionary {filename: checksum(filename)} for
                       each bento.info (including subentos)
db["package_description"] : pickled PackageDescription instance
db["user_flags"] : pickled user_flags dict
db["parsed_dict"]: pickled raw parsed dictionary (as returned by
                   raw_parse, before having been seen by the visitor)
"""
import os
import sys
import tempfile
import cPickle
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import warnings

from bento._config \
    import \
        DB_FILE, CHECKSUM_DB_FILE
from bento.core.parser.api \
    import \
        raw_parse
from bento.core.package \
    import \
        raw_to_pkg_kw, PackageDescription
from bento.core.options \
    import \
        raw_to_options_kw, PackageOptions
from bento.core.utils \
    import \
        ensure_dir, safe_write

class CachedPackage(object):
    __version__ = "1"
    __magic__ = "CACHED_PACKAGE_BENTOMAGIC"

    def _has_valid_magic(self, db):
        try:
            magic = db["magic"]
            if not magic == self.__magic__:
                return False
            else:
                return True
        except KeyError:
            return False

    def _reset(self):
        self.db = {}
        self.db["magic"] = CachedPackage.__magic__
        self.db["version"] = CachedPackage.__version__
        self._first_time = True

    def __init__(self, db_location=DB_FILE):
        self._location = db_location
        self._first_time = False
        if not os.path.exists(db_location):
            ensure_dir(db_location)
            self._reset()
        else:
            fid = open(db_location)
            try:
                self.db = cPickle.load(fid)
                if not self._has_valid_magic(self.db):
                    warnings.warn("Resetting invalid cached db")
                    self._reset()
            finally:
                fid.close()

            version = self.db["version"]
            if version != self.__version__:
                warnings.warn("Resetting invalid version of cached db")
                self._reset()

    def _has_invalidated_cache(self):
        if self.db.has_key("bentos_checksums"):
            r_checksums = cPickle.loads(self.db["bentos_checksums"])
            for f in r_checksums:
                checksum = md5(open(f).read()).hexdigest()
                if checksum != r_checksums[f]:
                    return True
            return False
        else:
            return True

    def get_package(self, filename, user_flags=None):
        if self._first_time:
            self._first_time = False
            return _create_package_nocached(filename, user_flags, self.db)
        else:
            if self._has_invalidated_cache():
                return _create_package_nocached(filename, user_flags, self.db)
            else:
                r_user_flags = cPickle.loads(self.db["user_flags"])
                if user_flags is None:
                    # FIXME: this case is wrong
                    return cPickle.loads(self.db["package_description"])
                elif r_user_flags != user_flags:
                    return _create_package_nocached(filename, user_flags, self.db)
                else:
                    raw = cPickle.loads(self.db["parsed_dict"])
                    pkg, files = _raw_to_pkg(raw, user_flags, filename)
                    return pkg

    def get_options(self, filename):
        if self._first_time:
            self._first_time = False
            return _create_options_nocached(filename, {}, self.db)
        else:
            if self._has_invalidated_cache():
                return _create_options_nocached(filename, {}, self.db)
            else:
                raw = cPickle.loads(self.db["parsed_dict"])
                return _raw_to_options(raw)

    def close(self):
        safe_write(self._location, lambda fd: cPickle.dump(self.db, fd))

    @classmethod
    def write_checksums(cls, target=CHECKSUM_DB_FILE):
        def _writer(fd):
            cache = cls()
            cPickle.dump(cPickle.loads(cache.db["bentos_checksums"]),
                         fd)
        safe_write(target, _writer)

    @classmethod
    def has_changed(cls, source=CHECKSUM_DB_FILE):
        fid = open(CHECKSUM_DB_FILE, "rb")
        try:
            checksums = cPickle.load(fid)
            for f, checksum in checksums.items():
                if checksum != md5(open(f).read()).hexdigest():
                    return True
            return False
        finally:
            fid.close()

def _create_package_nocached(filename, user_flags, db):
    pkg, options = _create_objects_no_cached(filename, user_flags, db)
    return pkg

def _create_options_nocached(filename, user_flags, db):
    pkg, options = _create_objects_no_cached(filename, user_flags, db)
    return options

def _raw_to_options(raw):
    kw = raw_to_options_kw(raw)
    return PackageOptions(**kw)

def _raw_to_pkg(raw, user_flags, filename):
    kw, files = raw_to_pkg_kw(raw, user_flags, filename)
    pkg = PackageDescription(**kw)
    return pkg, files

def _create_objects_no_cached(filename, user_flags, db):
    info_file = open(filename, 'r')
    try:
        data = info_file.read()
        raw = raw_parse(data, filename)

        pkg, files = _raw_to_pkg(raw, user_flags, filename)
        options = _raw_to_options(raw)

        checksums = [md5(open(f).read()).hexdigest() for f in files]
        db["bentos_checksums"] = cPickle.dumps(dict(zip(files, checksums)))
        db["package_description"] = cPickle.dumps(pkg)
        db["user_flags"] = cPickle.dumps(user_flags)
        db["parsed_dict"] = cPickle.dumps(raw)

        return pkg, options
    finally:
        info_file.close()
