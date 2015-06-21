from inspect import Signature, Parameter
from pathlib import Path

__all__ = ('Python34Type')

template="""
{0:class_decl}
{0:def_init}
{0:def_serialize}
"""



class Python34Type:
    def __init__(self, target, ir_type):
        self.target = target
        self.ir_type = ir_type
        self.outpath = Path('out/python34/types.py')

        self._preprocess_identifier()
        self._preprocess_params()
        self._preprocess_init_signature()
        self.member_inits = []


    def _preprocess_params(self):
        self.param_data = []
        for c in self.ir_type.constructors:
            for p in c.params:
                name = p.param_ident.full_ident
                kind = Parameter.POSITIONAL_OR_KEYWORD
                param = Parameter(name, kind)
                self.param_data.append({'constructor':c, 'ir_param':p, 'param':param})

    def _preprocess_init_signature(self):
        params = [p['param'] for p in self.param_data]
        self.init_signature = Signature(params)

    def _preprocess_identifier(self):
        self.identifier = self.ir_type.identifier.full_ident

    def preprocess_member_inits(self, types):
        self.member_inits = []
        for p in self.param_data:
            arg_ident = p['ir_param'].arg_type.identifier.full_ident
            param = p['param']
            if arg_ident in ['int', 'long', 'double', 'bool', 'string', 'bytes']:
                self.member_inits.append('self.{0} = {1}({0})'.format(param.name, arg_ident.capitalize()))
                continue
            raise Exception('NotImplemented: {}'.format(p))

    def validate(self):
        none_fields = [name for name, field in self.fields.items() if field is None]
        if none_fields:
            raise Exception('The following fields are undefined for TLType {}: {}'.format(self.ir_type.identifier, none_fields))

        if not self.fields['identifier'].isidentifier():
            raise Exception('Not a valid python identifier: {}'.format(self.identifier))

    def definition(self, validate=True):
        if validate:
            self.validate()
        return template.format(**self.fields)

    def class_decl(self):
        class_decl_template="""class {identifier}(TLType):"""
        return class_decl_template.format(identifier=self.identifier)

    def def_init(self):
        def_init_template="""
    def __init__{signature}:
        {member_inits}"""

        fields = dict(
            signature = str(self.init_signature),
            member_inits =  '\n        '.join(self.member_inits or ['raise NotImplemented'])
            )

        return def_init_template.format(**fields)

    def def_serialize(self):
        def_serialize_template="""
    def serialize(self):
        result = bytearray()
        {append_members}
        return bytes(result)"""

        am = []
        for p in self.param_data:
            param = p['param']
            am.append('result += {}.serialize()'.format(param.name))
        am = '\n        '.join(am)

        return def_serialize_template.format(append_members=am)

    def __format__(self, format_spec):
        if format_spec == 'type_definition':
            return template.format(self)
        if format_spec == 'class_decl':
            return self.class_decl()
        if format_spec == 'def_init':
            return self.def_init()
        if format_spec == 'def_serialize':
            return self.def_serialize()

        return super().__format__(format_spec)
