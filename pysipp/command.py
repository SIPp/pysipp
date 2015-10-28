'''
Command string rendering
'''
import string
from distutils import spawn
from copy import copy
from collections import OrderedDict
import utils

log = utils.get_logger()


def iter_format(item):
    return string.Formatter().parse(item)


class Field(object):
    def __init__(self, name, fmtstr):
        self.name = name
        self.fmtstr = fmtstr
        self.value = None

    def __get__(self, obj, cls):
        return self.value

    def __set__(self, obj, value):
        self.render(value)  # value checking
        self.value = value

    def render(self, value=None):
        return self.fmtstr.format(**{self.name: value}) if value else ''


class BoolField(Field):
    def __set__(self, obj, value):
        if not isinstance(value, bool):
            raise ValueError("{} must be a boolean type".format(self.name))
        self.value = value

    def render(self, value=None):
        return self.fmtstr.format(**{self.name: ''})


class DictField(object):
    def __init__(self, name, fmtstr):
        self.name = name
        self.fmtstr = fmtstr
        self.d = OrderedDict()

    def __get__(self, obj, cls):
        return self.d

    def __set__(self, obj, value):
        raise AttributeError

    def render(self, value=None):
        return ''.join(
            self.fmtstr.format(**{self.name: '{} {}'.format(key, val)})
            for key, val in self.d.items()
        )


def CmdStr(spec):
    '''Build a command string from an iterable of format string tokens.

    Given a `spec` (i.e. an iterable of format string specifiers), this
    object wraps a command string and allows for `str.format` "replacement
    fields" to be assigned using attribute access.

    Ex.
        >>> cmd = CmdStr('/usr/bin/sipp/, [
            '{remote_host}',
            ':{remote_port}',
            '-i {local_host} ',
            '-p {local_port} ',
            '-recv_timeout {msg_timeout} ',
            '-i {local_host} ',
        ]
        >>> str(cmd)
        '/usr/bin/sipp'

        >>> cmd.remote_host = 'doggy.com'
        >>> cmd.local_host = '192.168.0.1'
        >>> cmd.render()
        '/usr/bin/sipp doggy.com -i 192.168.0.1'

        >>> cmd.remote_port = 5060
        >>> str(cmd)
        '/usr/bin/sipp doggy.com:5060 -i 192.168.0.1'
    '''
    class Renderer(object):
        template = tuple(spec)
        _params = OrderedDict()

        def __init__(self):
            self._init = True  # lock attribute creation

        def __str__(self):
            return self.render()

        def render(self):
            tokens = []
            for key, descr in self._params.items():
                # trigger descriptor protocol `__get__`
                value = getattr(self, key)
                if value is not None:
                    tokens.append(descr.render(value))

            return ''.join(tokens)

        def __setattr__(self, key, value):
            # immutable after instantiation
            if getattr(self, '_init', False) and\
                    key not in self.__class__.__dict__:
                raise AttributeError(key)
            object.__setattr__(self, key, value)

        def copy(self):
            return copy(self)

    # build renderer type with custom descriptors
    for fmtstr in spec:
        if isinstance(fmtstr, tuple):
            fmtstr, descriptor = fmtstr
        else:
            descriptor = Field
        fieldname = list(iter_format(fmtstr))[0][1]
        descr = descriptor(fieldname, fmtstr)
        Renderer._params[fieldname] = descr
        setattr(Renderer, fieldname, descr)

    return Renderer()


sipp_spec = [
    # contact info
    '{prefix} ',
    '{bin_path} ',
    '{remote_host}',  # NOTE: no space
    ':{remote_port} ',
    '-i {local_host} ',
    '-p {local_port} ',
    '-s {uri_username} ',
    '-rsa {proxy_addr}',  # NOTE: no space
    ':{proxy_port} ',
    '-auth_uri {auth_uri} ',
    # sockets and protocols
    '-bind_local {bind_local} ',
    '-mi {media_addr} ',
    '-mp {media_port} ',
    '-t {transport} ',
    # scenario config/ctl
    '-sn {scen_name} ',
    '-sf {scen_file} ',
    '-recv_timeout {recv_timeout} ',
    '-d {pause_duration} ',
    '-default_behaviors {default_behaviors} ',
    '-3pcc {3pcc} ',
    # SIP vars
    '-cid_str {cid_str} ',
    '-base_cseq {base_cseq} ',
    '-ap {auth_password} ',
    # load settings
    '-r {rate} ',
    '-l {limit} ',
    '-m {call_count} ',
    '-rp {rate_period} ',
    # data insertion
    ('-key {key_vals} ', DictField),
    ('-set {global_vars} ', DictField),
    # files
    '-error_file {error_file} ',
    '-calldebug_file {calldebug_file} ',
    '-message_file {message_file} ',
    '-log_file {log_file} ',
    '-inf {info_file} ',
    '-screen_file {screen_file} ',
    # bool flags
    ('-rtp_echo {rtp_echo}', BoolField),
    ('-timeout_error {timeout_error}', BoolField),
    ('-aa {auto_answer}', BoolField),
    ('-trace_err {trace_err}', BoolField),
    ('-trace_calldebug {trace_calldebug}', BoolField),
    ('-trace_msg {trace_msg}', BoolField),
    ('-trace_logs {trace_logs}', BoolField),
    ('-trace_screen {trace_screen}', BoolField),
    ('-error_overwrite {error_overwrite}', BoolField),
]


def SippCmd(spec=sipp_spec, fields=None):
    '''A command string renderer for `sipp`.

    Given the provided `spec` create a cmd string renderer type.
    '''
    cmd = CmdStr(spec)
    cmd.bin_path = spawn.find_executable('sipp')
    return cmd
