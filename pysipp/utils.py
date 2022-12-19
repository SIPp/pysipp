import importlib
import inspect
import logging
import os
import tempfile
import types

LOG_FORMAT = (
    "%(asctime)s %(threadName)s [%(levelname)s] %(name)s "
    "%(filename)s:%(lineno)d : %(message)s"
)

DATE_FORMAT = "%b %d %H:%M:%S"


def load_source(name: str, path: str) -> types.ModuleType:
    """
    Replacement for deprecated imp.load_source()
    Thanks to:
    https://github.com/epfl-scitas/spack for pointing out the
    important missing "spec.loader.exec_module(module)" line.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_logger():
    """Get the project logger instance"""
    return logging.getLogger("pysipp")


def log_to_stderr(level="INFO", **kwargs):
    defaults = {"format": LOG_FORMAT, "level": level}
    defaults.update(kwargs)
    logging.basicConfig(**defaults)


def get_tmpdir():
    """Return a random temp dir"""
    return tempfile.mkdtemp(prefix="pysipp_")


def load_mod(path, name=None):
    """Load a source file as a module"""
    name = name or os.path.splitext(os.path.basename(path))[0]
    # load module sources
    return load_source(name, path)


def iter_data_descrs(cls):
    """Deliver all public data-descriptors (for properties only if `fset` is
    defined) as `name`, `attr`, pairs
    """
    for name in dir(cls):
        attr = getattr(cls, name)
        if inspect.isdatadescriptor(attr):
            if (hasattr(attr, "fset") and not attr.fset) or "_" in name[0]:
                continue
            yield name, attr


def DictProxy(d, keys, cls=None):
    """A dictionary proxy object which provides attribute access to the
    elements of the provided dictionary `d`
    """

    class DictProxyAttr(object):
        """An attribute which when modified proxies to an instance dictionary
        named `dictname`.
        """

        def __init__(self, key):
            self.key = key

        def __get__(self, obj, cls):
            if obj is None:
                return self
            return d.get(self.key)

        def __set__(self, obj, value):
            d[self.key] = value

    # provide attribute access for all named keys
    attrs = {key: DictProxyAttr(key) for key in keys}

    if cls is not None:
        # apply all attributes on provided type
        for name, attr in attrs.items():
            setattr(cls, name, attr)
    else:
        # delegate some methods to the original dict
        proxied_attrs = [
            "__repr__",
            "__getitem__",
            "__setitem__",
            "__contains__",
            "__len__",
            "get",
            "update",
            "setdefault",
        ]
        attrs.update({attr: getattr(d, attr) for attr in proxied_attrs})

        # construct required default methods
        def init(self):
            self.__dict__ = d

        attrs.update({"__init__": init})

        # render a new type
        return type("DictProxy", (), attrs)
