import logging
import imp  # XXX py2.7
import tempfile
import os

LOG_FORMAT = ("%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d "
              ": %(message)s")
DATE_FORMAT = '%b %d %H:%M:%S'


def get_logger():
    return logging.getLogger('pysipp')


def get_tmpdir():
    return tempfile.mkdtemp(prefix='pysipp_')


def load_mod(path, name=None):
    """Load a source file as a module
    """
    name = name or os.path.splitext(os.path.basename(path))[0]
    # load module sources
    return imp.load_source('pysipp_confpy', path)
