'''
Command string rendering
'''
import string
from distutils import spawn
from copy import copy
import utils

log = utils.get_logger()


def iter_format(item):
    return string.Formatter().parse(item)


class CmdStr(object):
    '''Build a command string from an iterable of format string tokens.

    Given a `template` (i.e. an iterable of format string specifiers), this
    object wraps a command string and allows for `str.format` "replacement
    fields" to be assigned using attribute access. Tokens are rendered only if
    all replacement fields are assigned.

    Ex.
        >>> cmd = CmdStr('/usr/bin/sipp/, [
            '{remote_host}:{remote_port}',
            '-i {local_host}',
            '-p {local_port}',
            '-recv_timeout {msg_timeout}',
            '-i {local_host}',
        ]
        >>> str(cmd)
        '/usr/bin/sipp'

        >>> cmd.remote_host = 'doggy.com'
        >>> cmd.local_host = '192.168.0.1'
        >>> cmd.render()
        # both remote_host AND remote_port must be set to render token
        '/usr/bin/sipp -i 192.168.0.1'

        >>> cmd.remote_port = 5060
        >>> str(cmd)
        '/usr/bin/sipp doggy.com:5060 -i 192.168.0.1'
    '''
    def __init__(self, program, template):
        self.prog = program
        self.template = tuple(template)  # iter of tokens
        self._params = set()
        for item in self.template:
            for _, name, fspec, conversion in iter_format(item):
                self._params.add(name)
                self.__dict__[name] = None
        self._init = True  # lock attribute creation

    def __str__(self):
        return self.render()

    def render(self):
        # build a content map of format string 'fields' to values
        content = {}
        for key in self._params:
            value = self.__dict__[key]
            if value is not None:
                content[key] = value

        # filter to tokens with assigned values
        tokens = []
        for item in self.template:
            fields = set()
            for _, name, fspec, conversion in iter_format(item):
                if name:
                    fields.add(name)
                else:
                    tokens.append(item)

            if all(field in content for field in fields):
                # only accept tokens for which we have all field values
                tokens.append(item)

        # log.debug("fields are '{}'".format(fields))
        # log.debug("content is '{}'".format(content))
        return ' '.join([self.prog] + tokens).format(**content)

    def __setattr__(self, key, value):
        # immutable after instantiation
        if getattr(self, '_init', False) and key not in self.__dict__:
            raise AttributeError(key)
        object.__setattr__(self, key, value)

    def copy(self):
        return copy(self)


def SippCmd(spec, fields=None):
    '''A command string renderer for `sipp`.

    Given the provided `spec` create a cmd string renderer type.
    '''
    sipp = spawn.find_executable('sipp')
    return CmdStr(sipp, spec)
