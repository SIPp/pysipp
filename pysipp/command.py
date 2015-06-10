'''
Command string rendering
'''
from distutils import spawn
from copy import copy


class CmdStr(object):
    '''Build a command string from an iterable of format string tokens
    '''
    def __init__(self, program, template):
        self.prog = program
        self.template = tuple(template)  # list of tokens
        self._params = set()
        for i, item in enumerate(template):
            for _, name, fspec, conversion in item._formatter_parser():
                self._params.add(name)
                self.__dict__[name] = None
        self._init = True  # lock attribute creation

    def render(self):
        # build a content map of format string 'fields' to values
        content = {}
        for key in self._params:
            value = self.__dict__[key]
            if value is not None:
                content[key] = value

        # filter acceptable tokens
        tokens = []
        for item in self.template:
            parser = item._formatter_parser()
            fields = set()
            for _, name, fspec, conversion in parser:
                if name:
                    fields.add(name)
            # print("fields '{}'".format(fields))
            # print("content '{}'".format(content))
            if all(field in content for field in fields):
                # only accept tokens for which we have all field values
                tokens.append(item)

        return ' '.join([self.prog] + tokens).format(**content)

    def __setattr__(self, key, value):
        # immutable after instatiation
        if getattr(self, '_init', False) and key not in self.__dict__:
            raise AttributeError(key)
        object.__setattr__(self, key, value)

    def copy(self):
        return copy(self)


def SippCmd(fields=None):
    '''A command string renderer for `sipp`
    '''
    sipp = spawn.find_executable('sipp')
    spec = (
        '{remote_host}:{remote_port}',
        '-i {local_ip}',
        '-p {local_port}',
        '-recv_timeout {msg_timeout}',
        '-sn {scen_name}',
        '-s {uri_username}',
        '-rsa {proxy}',
        # load settings
        '-d {duration}',
        '-r {rate}',
        '-l {limit}',
        '-m {call_count}'
    ) + tuple(fields) if fields else ()
    return CmdStr(sipp, spec)
