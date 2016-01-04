"""
Load files from scenario directories
"""
import glob
import os
import utils
log = utils.get_logger()


class CollectionError(Exception):
    """Scenario dir collection error
    """


def glob_for_scripts(directory):
    '''Find scenario xml scripts and conf.py in script dir
    '''
    xmls = glob.iglob(directory+'/*.xml')
    # double check
    xmls = [f for f in xmls if 'xml' in os.path.splitext(f)[1]]
    confpy = glob.glob(directory+'/pysipp_conf.py')
    if len(confpy) == 1:
        confpy = confpy[0]
    elif len(confpy) > 1:
        raise ValueError(
            'can only be at most one pysipp_conf.py in scen directory!'
        )
        log.debug("discovered xmls:\n{}".format('\n'.join(xmls)))
    return xmls, confpy


def iter_scen_dirs(rootdir, dir_filter=lambda dir_name: dir_name):
    '''Build a map of SIPp scripts by searching the filesystem for .xml files

    :param str rootdir: dir in the filesystem to start scanning for xml files
    :return: an iterator over all scenario dirs yielding tuples of the form
        (<filepath (str)>, <xmlpaths (list)>, <confpypath (str)>)
    '''
    for path, dirnames, filenames in os.walk(rootdir):

        # filter the path dirs to traverse as we recurse the file system
        # (only use if you know what you're doing)
        dirnames[:] = filter(dir_filter, dirnames)

        path = os.path.abspath(path)
        xmls, confpy = glob_for_scripts(path)
        if not len(xmls) and not confpy:
            log.warn(
                "No pysipp related files were found when searching for SIPp "
                "scenarios under '{}'".format(path))
            continue
        elif not len(xmls):
            log.warn(
                "No xml scripts were found when searching for SIPp scenarios "
                "under '{}'".format(path))

        # load module sources
        confpy = utils.load_mod(confpy, name='pysipp_confpy') if confpy else None

        yield path, xmls, confpy
