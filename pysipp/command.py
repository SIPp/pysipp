'''
Command string rendering
'''
import string
from copy import copy
from collections import OrderedDict
import utils

log = utils.get_logger()


def iter_format(item):
    return string.Formatter().parse(item)


class Field(object):
    _default = None

    def __init__(self, name, fmtstr):
        self.name = name
        self.fmtstr = fmtstr

    def __get__(self, obj, cls):
        if obj is None:
            return self
        return obj._values.setdefault(
            self.name, self._default() if self._default else None,
        )

    def __set__(self, obj, value):
        self.render(value)  # value checking
        obj._values[self.name] = value

    def render(self, value):
        return self.fmtstr.format(
            **{self.name: "'{}'".format(value)}) if value else ''


class AddrField(Field):
    def render(self, value):
        return self.fmtstr.format(
            **{self.name: "'[{}]'".format(value)}) if value else ''


class BoolField(Field):
    def __set__(self, obj, value):
        if not isinstance(value, bool):
            raise ValueError("{} must be a boolean type".format(self.name))
        super(type(self), self).__set__(obj, value)

    def render(self, value):
        return self.fmtstr.format(**{self.name: ''})


class DictField(Field):
    _default = OrderedDict

    def render(self, value):
        return ''.join(
            self.fmtstr.format(**{self.name: "{} '{}'".format(key, val)})
            for key, val in value.items()
        )


def cmdstrtype(spec):
    '''Build a command str renderer from an iterable of format string tokens.

    Given a `spec` (i.e. an iterable of format string specifiers), this
    function returns a command string renderer type which allows for
    `str.format` "replacement fields" to be assigned using attribute access.

    Ex.
        >>> cmd = cmdstrtype([
            '{bin_path} '
            '{remote_host} ',
            ':{remote_port} ',
            '-i {local_host} ',
            '-p {local_port} ',
            '-recv_timeout {msg_timeout} ',
            '-i {local_host} ',
        ])()
        >>> cmd.bin_path = '/usr/bin/sipp/'
        >>> str(cmd)
        '/usr/bin/sipp'
        >>> str(cmd) == cmd.render()
        True
        >>> cmd.remote_host = 'doggy.com'
        >>> cmd.local_host = '192.168.0.1'
        >>> cmd.render()
        '/usr/bin/sipp doggy.com -i 192.168.0.1'
        >>> cmd.remote_port = 5060
        >>> cmd.render()
        '/usr/bin/sipp doggy.com:5060 -i 192.168.0.1'
    '''
    class Renderer(object):
        _params = OrderedDict()

        def __init__(self, defaults=None):
            self._values = {}
            if defaults:
                for name, value in defaults.items():
                    setattr(self, name, value)
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
            if getattr(
                self, '_init', False
            ) and (
                key not in self.__class__.__dict__
            ) and (
                key not in self._params
            ) and key[0] is not '_':
                raise AttributeError(
                    "no settable public attribute '{}' defined".format(key))
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

    return Renderer


sipp_spec = [
    # contact info
    '{prefix} ',
    '{bin_path} ',
    ('{remote_host}', AddrField),  # NOTE: no space
    ':{remote_port} ',
    ('-i {local_host} ', AddrField),
    '-p {local_port} ',
    '-s {uri_username} ',
    ('-rsa {proxy_addr}', AddrField),  # NOTE: no space
    ':{proxy_port} ',
    '-auth_uri {auth_uri} ',
    # sockets and protocols
    '-bind_local {bind_local} ',
    ('-mi {media_addr} ', AddrField),
    '-mp {media_port} ',
    '-t {transport} ',
    # scenario config/ctl
    '-sn {scen_name} ',
    '-sf {scen_file} ',
    '-recv_timeout {recv_timeout} ',
    '-timeout {timeout} ',
    '-d {pause_duration} ',
    '-default_behaviors {default_behaviors} ',
    '-3pcc {sock3pcc} ',
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
    ('-trace_err {trace_error}', BoolField),
    ('-trace_calldebug {trace_calldebug}', BoolField),
    ('-trace_msg {trace_message}', BoolField),
    ('-trace_logs {trace_log}', BoolField),
    ('-trace_screen {trace_screen}', BoolField),
    ('-error_overwrite {error_overwrite}', BoolField),
]


# a SIPp cmd renderer
SippCmd = cmdstrtype(sipp_spec)
