from collections import OrderedDict
from inspect import Signature, Parameter
from .param import Python34Parameter
from .ident import Python34Identifier
import sys

template="""
class {identifier}:
    number = pack_number({number:#x})
    is_base = False
    _data_cls = namedtuple('{result_type}', [{result_type_params}])

    @staticmethod
    def serialize(data=None):
        {serialize}

    @staticmethod
    def deserialize(io_bytes):
        {deserialize}
combinators[{identifier}.number] = {identifier}
"""


class Python34Combinator:
    def __init__(self, ident, params, result_type, ir_combinator):
        self._ident = ident
        self._params = params
        self._result_type = result_type
        self._ir_combinator = ir_combinator

        result_type.add_constructor(self)


    def _set_result_type(self):
        result = self._ir_combinator.result_type
        result_type = self.target.types[result.identifier.full_ident]
        result_type.constructors[self._ir_combinator.identifier.full_ident] = self
        self._result_type = result_type

    @property
    def identifier(self):
        return self._ident.py3ident

    @property
    def ident(self):
        return self._ident

    @property
    def number(self):
        return self._ir_combinator.number

    @property
    def params(self):
        return self._params

    @property
    def py3ident(self):
        ident = '{}_c'.format(self._ident.py3ident)

        Python34Identifier.validate(ident)

        return ident
    
    def _template_identifier(self):
        return self.py3ident

    def _template_get_params(self):
        get_params = ['{} = {}.deserialize(io_bytes)'.format(p.py3ident, p.arg_type.py3ident) for p in self.params]
        return '\n        '.join(get_params)

    def _template_result_type_params(self):
        get_params = ["'{}'".format(p.py3ident) for p in self.params]
        if not get_params:
            get_params = ["'tag'", "'number'"]
        return ', '.join(get_params)

    #def _template_result_type_params(self):
    #    get_params = ["_{0} = combinators[{number:#x}]".format(p.py3ident) for p in self.params]
    #    return ', '.join(get_params)

    def _template_result_type(self):
        return self.result_type.py3ident

    def _template_deserialize_no_params(self):
        lines = [
            'number = io_bytes.read(4)',
            'assert {}.number == number'.format(self._template_identifier()),
            "return {0}._data_cls(tag='{1}', number={0}.number)".format(self._template_identifier(),
                                                                  self.ident.ir_ident.ident_full)
        ]
        return '\n        '.join(lines)

    def _template_deserialize(self):
        if self.params:
            return self._template_deserialize_params()
        else:
            return self._template_deserialize_no_params()

    def _template_deserialize_params(self):

        result_args =  []
        for param in self.params:
            arg_type = param.arg_type
            p = 'raise Exception("unimplemented")'
            if arg_type.py3ident in ['Int', 'Long', 'Double', 'String', 'Bytes']:
                p = '{} = {}_c.deserialize(io_bytes)'.format(param.py3ident, arg_type.py3ident.lower())
            else:
                p = '{} = deserialize(io_bytes)'.format(param.py3ident)

            result_args.append(p)

        ret_stmt = 'return {}._data_cls('.format(self._template_identifier())

        result_args = [result_args[0]] + [r.rjust(len(ret_stmt) + len(r) + 8) for r in result_args[1:]]
        result_args = ',\n'.join(result_args)
        ret_stmt = '{}{})'.format(ret_stmt, result_args)

        return ret_stmt

    def _template_serialize_params(self):
        lines = []
        lines += ['result = bytearray()']

        result_args =  []
        for param in self.params:
            arg_type = param.arg_type
            p = 'result += {}_c.serialize(data.{})'.format(arg_type.py3ident.lower(), param.py3ident)

            result_args.append(p)

        lines += result_args
        lines += ['return bytes(result)']
        lines = '\n        '.join(lines)

        return lines

    def _template_serialize_no_params(self):
        return 'return {}.number'.format(self._template_identifier())

    def _template_serialize(self):
        if self.params:
            return self._template_serialize_params()
        else:
            return self._template_serialize_no_params()

    @property
    def result_type(self):
        return self._result_type

    def definition(self):
        return template.format(
            identifier=self._template_identifier(), 
            number=self.number, 
            result_type_params=self._template_result_type_params(),
            result_type=self._template_result_type(),
            deserialize=self._template_deserialize(),
            serialize=self._template_serialize()
            )

    def __str__(self):
        return '{}#{:x}'.format(self.identifier, self.number)
