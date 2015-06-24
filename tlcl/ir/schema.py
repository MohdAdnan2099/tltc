import sys
import re
from abc import ABCMeta, abstractmethod
from pathlib import Path
import zlib
from pprint import PrettyPrinter

from ..syntax.tlsyntax import TLSyntax
from .type import IRType
from .identifier import IRIdentifier
from .param import IRParameter
from .combinator import IRCombinator

from collections import OrderedDict

def _get_builtin_types():
    Type_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'Type'))
    nat_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, '#'))

    Int_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'Int'))
    Long_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'Long'))
    Double_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'Double'))
    String_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'String'))
    Bytes_t = IRType(IRType.BOXED, IRIdentifier(IRIdentifier.TYPE, None, 'Bytes'))

    return {'#':nat_t, 'Type':Type_t, 'Int':Int_t, 'Long':Long_t, 'Double':Double_t, 'String':String_t, 'Bytes':Bytes_t}

def _get_builtin_combinators():
    t = _get_builtin_types()

    _int = IRCombinator(IRCombinator.CONSTRUCTOR,
        IRIdentifier(IRIdentifier.COMBINATOR, None, 'int'),
        zlib.crc32('int ? = Int'.encode()),
        result_type=t['Int']
        )

    _long = IRCombinator(IRCombinator.CONSTRUCTOR,
        IRIdentifier(IRIdentifier.COMBINATOR, None, 'long'),
        zlib.crc32('long ? = Long'.encode()),
        result_type=t['Long']
        )

    _double = IRCombinator(IRCombinator.CONSTRUCTOR,
        IRIdentifier(IRIdentifier.COMBINATOR, None, 'double'),
        zlib.crc32('double ? = Double'.encode()),
        result_type=t['Double']
        )

    _string = IRCombinator(IRCombinator.CONSTRUCTOR,
        IRIdentifier(IRIdentifier.COMBINATOR, None, 'string'),
        zlib.crc32('string ? = String'.encode()),
        result_type=t['String']
        )

    _bytes = IRCombinator(IRCombinator.CONSTRUCTOR,
        IRIdentifier(IRIdentifier.COMBINATOR, None, 'bytes'),
        zlib.crc32('bytes ? = Bytes'.encode()),
        result_type=t['Bytes']
        )

    return {str(_int):_int, str(_long):_long, str(_double):_double, str(_string):_string, str(_bytes):_bytes}

class IRSchema:
    def __init__(self, schema):
        self._schema = schema
        self._construct_iter_expressions()
        self.types = OrderedDict()
        self.combinator_identifiers = []
        self.combinator_numbers = []
        self.combinators = OrderedDict()

    def _construct_iter_expressions(self):
        tokens = [
            # constructor's full identifier
            '(?P<combinator>'
                '(?:(?P<combinator_namespace>{lc-ident-ns})\.|)'
                '(?P<combinator_identifier>\S+)'
                '#(?P<combinator_id>{hex-digit}+)'
            ')'.format(**TLSyntax.TL),
            # optional parameter names and types
            '(?P<optional_parameter>'
                '\{{'
                    '(?P<optional_parameter_identifier>\S+):'
                    '(?P<optional_parameter_type>'
                        '(?:(?P<optional_parameter_type_namespace>{lc-ident-ns})\.|)'
                        '(?P<optional_parameter_type_identifier>\S+)'
                    ')'
                '\}}'
            ')'.format(**TLSyntax.TL),
            # parameter's names and types
            '(?P<parameter>'
                '(?:'
                    '(?P<parameter_identifier>\S+):'
                    '(?P<parameter_type>'
                        '(?P<vector_parameter>Vector<|)'
                        '(?:(?P<parameter_type_namespace>{lc-ident-ns})\.|)'
                        '(?P<parameter_type_identifier>[^\s>]+)'
                        '(?:>|)'
                    ')'
                ')'
                '|(?P<parameter_nat>'
                    '#'
                ')'
                '|\[\s+'
                    '(?P<parameter_multiplicity>\S+)'
                  '\s+\]'
            ')'.format(**TLSyntax.TL),

            # get the combinator's Type
            '=\s*'
            '(?P<combinator_result_type>'
                '(?:(?P<combinator_result_type_namespace>{lc-ident-ns})\.|)'
                '(?P<combinator_result_type_identifier>Vector t|Vector|[^;]+)'
                '(:?<(?P<result_vector_type>.*?)>|)'
            ')'.format(**TLSyntax.TL),

            # end of constructor
            '(?P<combinator_end>;)',

            # start the function section
            '(?P<start_functions>{triple-minus}functions{triple-minus})'.format(**TLSyntax.TL),

            # start the types section
            '(?P<start_types>{triple-minus}types{triple-minus})'.format(**TLSyntax.TL),

            # catch anything else
            '(?P<invalid_syntax>\S+)'
        ]
        #print(tokens[3], file=sys.stderr)
        self.iter_expr = '(?:{})'.format('|'.join(tokens))
        self.iter_prog = re.compile(self.iter_expr)

    def create_new_combinator(self, kind, namespace, ident, number):
        identifier = IRIdentifier(IRIdentifier.COMBINATOR, namespace, ident)

        if identifier in self.combinator_identifiers:
            raise Exception('Combinator with identifier already exists: \'{}\''.format(identifier))

        if number in self.combinator_numbers:
            raise Exception('Combinator with number already exists: \'{:x}\''.format(number))

        combinator = IRCombinator(kind, identifier, number)

        self.combinator_numbers.append(number)
        self.combinator_identifiers.append(identifier)
        self.combinators[str(combinator.lc_ident_full)] = combinator
       
        return combinator

    def create_new_type(self, namespace, ident, vector_type=None):
        identifier = IRIdentifier(IRIdentifier.TYPE, namespace, ident, vector_type)
        ir_type = IRType(IRType.BOXED, identifier, vector_type)
        self.types[identifier] = ir_type
        return ir_type


    def _fsm_combinators(self, groups, section):
        if section == 'constructors' and groups['start_functions']:
            return 'combinators', {'section':'functions'}

        if not groups['combinator']:
            return 'error', {'groups': groups}

        namespace = groups['combinator_namespace']
        identifier = groups['combinator_identifier']
        number = int(groups['combinator_id'], 16)

        if section not in ['functions', 'constructors']:
            return 'error', {'groups', groups}

        kind = IRCombinator.CONSTRUCTOR if section == 'constructors' else IRCombinator.FUNCTION

        combinator = self.create_new_combinator(kind, namespace, identifier, number)

        return 'combinator_optional_params', {'combinator': combinator, 'section':section}

    def _fsm_combinator_optional_params(self, groups, section, combinator):
        if not groups['optional_parameter']:
            return self._fsm_combinator_params(groups, section, combinator)

        param_ident = IRIdentifier(IRIdentifier.PARAMETER, None, groups['optional_parameter_identifier'])
        arg_ident = IRIdentifier(IRIdentifier.TYPE, groups['optional_parameter_type_namespace'], groups['optional_parameter_type_identifier'])
        arg_type = IRType(IRType.BOXED, arg_ident)
        param = IRParameter(IRParameter.OPT_ARG, param_ident, arg_type)

        combinator.add_parameter(param)

        return 'combinator_optional_params', {'combinator':combinator, 'section':section}

    def _fsm_combinator_params(self, groups, section, combinator):
        if not groups['parameter']:
            return self._fsm_combinator_result_type(groups, section, combinator)

        t = None
        param = None

        if groups['parameter_nat'] is not None:
            param_ident = IRIdentifier(IRIdentifier.PARAMETER, None, '#')
            arg_ident = IRIdentifier(IRIdentifier.TYPE, None, '#')
            arg_type = IRType(IRType.NAT, arg_ident)
            param = IRParameter(IRParameter.ARG_NAT, param_ident, arg_type)
        elif groups['parameter_multiplicity'] is not None:
            param_ident = IRIdentifier(IRIdentifier.TEMPLATE, None, None)
            arg_ident = IRIdentifier(IRIdentifier.TYPE, None, 't')
            arg_type = IRType(IRType.TEMPLATE, arg_ident)
            param = IRParameter(IRParameter.MULT, param_ident, arg_type)
        else:
            param_ident = IRIdentifier(IRIdentifier.PARAMETER, None, groups['parameter_identifier'])
            arg_ident = IRIdentifier(IRIdentifier.TYPE, groups['parameter_type_namespace'], groups['parameter_type_identifier'])

            arg_type = None
            if arg_ident.is_bare():
                arg_type = IRType(IRType.BARE, arg_ident.boxed())
            else:
                arg_type = IRType(IRType.BOXED, arg_ident)
            param = IRParameter(IRParameter.ARG, param_ident, arg_type)

        combinator.add_parameter(param)

        return 'combinator_params', {'combinator':combinator, 'section':section}

    def _fsm_combinator_result_type(self, groups, section, combinator):
        if not groups['combinator_result_type']:
            return 'error', {'groups':groups}

        t = self.types.get(groups['combinator_result_type'], None)
        #print (groups['combinator_result_type'])
        if t is None:
            namespace = groups['combinator_result_type_namespace']
            ident = groups['combinator_result_type_identifier']
            vector_type = None
            if groups['result_vector_type']:
                print(groups['result_vector_type'], file=sys.stderr)
                vector_type = self.types.get(groups['result_vector_type'])
            t = self.create_new_type(namespace, ident, vector_type)

        combinator.set_result_type(t)

        return 'combinator_end', {'section':section}

    def _fsm_combinator_end(self, groups, section):
        if not groups['combinator_end']:
            return 'error', {}

        return 'combinators', {'section':section}

    def _fsm_error(self, matches, *args, **kwargs):
        pp = PrettyPrinter(indent=4, stream=sys.stderr)
        matches = {k:v for k,v in matches.items() if v is not None}
        if 'groups' in kwargs:
            groups = {k:v for k,v in kwargs['groups'].items() if v is not None}
            del kwargs['groups']
            pp.pprint(groups)
        
        pp.pprint(matches)
        pp.pprint(kwargs)
        raise Exception('ERROR: in \'{}\':'.format(''))

    def print_combinators(self, func=repr):
        for name, combinator in self.combinators.items():
            print(repr(combinator))

    def generate_ir(self):
        for name, ir_type in _get_builtin_types().items():
            self.types[ir_type.ident_full] = ir_type

        for name, ir_combinator in _get_builtin_combinators().items():
            self.combinator_numbers.append(ir_combinator.number)
            self.combinator_identifiers.append(name)
            self.combinators[ir_combinator.lc_ident_full] = ir_combinator

        schema_iter = self.iter_prog.finditer(self._schema)
        kwargs = {'section': 'constructors'}
        state = 'combinators'
        for i in schema_iter:
            func = getattr(self, '_fsm_{}'.format(state))
            state, kwargs = func(i.groupdict(), **kwargs)

            if state == 'quit':
                self._fsm_error(i, kwargs)
