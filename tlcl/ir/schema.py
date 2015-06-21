import sys
import re
from abc import ABCMeta, abstractmethod
from pathlib import Path

from ..syntax.tlsyntax import TLSyntax
from .type import IRType
from .identifier import IRIdentifier
from .param import IRParameter
from .combinator import IRCombinator

from collections import OrderedDict

class IRSchema:
    def __init__(self, schema):
        self._schema = schema
        self._construct_iter_expressions()
        self.types = OrderedDict()
        self.combinators_by_number = OrderedDict()
        self.combinators_by_identifier = OrderedDict()
        self.combinators = []

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
                        '(?:(?P<parameter_type_namespace>{lc-ident-ns})\.|)'
                        '(?P<parameter_type_identifier>\S+)'
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
                '(?P<combinator_result_type_identifier>[^;]+)'
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
        self.iter_expr = '(?:{})'.format('|'.join(tokens))
        self.iter_prog = re.compile(self.iter_expr)

    def create_new_combinator(self, kind, namespace, ident, number):
        identifier = IRIdentifier(IRIdentifier.COMBINATOR, namespace, ident)

        if identifier.full_ident in self.combinators_by_identifier:
            raise Exception('Combinator with identifier already exists: \'{:x}\''.format(identifier.full_ident))

        if number in self.combinators_by_number:
            raise Exception('Combinator with number already exists: \'{:x}\''.format(number))

        combinator = IRCombinator(kind, identifier, number)

        self.combinators_by_number[number] = combinator
        self.combinators_by_identifier[identifier.full_ident] = combinator
       
        return combinator

    def create_new_type(self, namespace, ident):
        identifier = IRIdentifier(IRIdentifier.TYPE, namespace, ident)
        ir_type = IRType(identifier)
        self.types[identifier.full_ident] = ir_type
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
        arg_type = IRType(arg_ident)
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
            arg_type = IRType(arg_ident)
            param = IRParameter(IRParameter.ARG_NAT, param_ident, arg_type)
        elif groups['parameter_multiplicity'] is not None:
            param_ident = IRIdentifier(IRIdentifier.PARAMETER, None, 't')
            arg_ident = IRIdentifier(IRIdentifier.TYPE, None, 't')
            arg_type = IRType(arg_ident)
            param = IRParameter(IRParameter.MULT, param_ident, arg_type)
        else:
            param_ident = IRIdentifier(IRIdentifier.PARAMETER, None, groups['parameter_identifier'])
            arg_ident = IRIdentifier(IRIdentifier.TYPE, groups['parameter_type_namespace'], groups['parameter_type_identifier'])
            arg_type = IRType(arg_ident)
            param = IRParameter(IRParameter.ARG, param_ident, arg_type)

        combinator.add_parameter(param)

        return 'combinator_params', {'combinator':combinator, 'section':section}

    def _fsm_combinator_result_type(self, groups, section, combinator):
        if not groups['combinator_result_type']:
            return 'error', {'groups':groups}

        t = self.types.get(groups['combinator_result_type'], None)
        if t is None:
            namespace = groups['combinator_result_type_namespace']
            ident = groups['combinator_result_type_identifier']
            t = self.create_new_type(namespace, ident)

        combinator.set_result_type(t)

        return 'combinator_end', {'section':section}

    def _fsm_combinator_end(self, groups, section):
        if not groups['combinator_end']:
            return 'error', {}

        return 'combinators', {'section':section}

    def _fsm_error(self, matches, **kwargs):
        print('_fsm_error')
        print('ERROR:\t{}:\t{}'.format(matches, kwargs))
        return 'quit', {}

    def print_combinators(self, func=repr):
        for key, val in self.combinators_by_number.items():
            print('{}'.format(func(val)))

    def generate_ir(self):
        schema_iter = self.iter_prog.finditer(self._schema)
        kwargs = {'section': 'constructors'}
        state = 'combinators'
        for i in schema_iter:
            func = getattr(self, '_fsm_{}'.format(state))
            state, kwargs = func(i.groupdict(), **kwargs)

            if state == 'quit':
                return _fsm_error(i, kwargs)

