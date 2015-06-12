
from abc import ABCMeta, abstractmethod
import numbers
import struct

"""
Types used as base classes for TL combinators and types
"""
class TLType(metaclass=ABCMeta):
    @abstractmethod
    def serialize(self):
        raise NotImplemented


class TLCombinator(metaclass=ABCMeta):
    combinators = {}

    @staticmethod
    def add_combinator(combinator_type):
        TLCombinator.combinators[combinator.number] = combinator_type

    @staticmethod
    @abstractmethod
    def serialize(obj):
        raise NotImplemented

    @staticmethod
    @abstractmethod
    def deserialize(self, bytes_io):
        raise NotImplemented


class TLConstructor(TLCombinator):
    pass


class TLFunction(TLCombinator):
    pass

"""
Predefined identifer / types in TL. https://core.telegram.org/mtproto/TL-formal
"""

class _Number(numbers.Number, TLType):
    def __init__(self, _data):
        self._data = self.internal_data_type(_data)

    @property
    @abstractmethod
    def internal_data_type(self):
        raise NotImplemented 

    @property
    @abstractmethod
    def result_type_class(self):
        raise NotImplemented 

class _Complex(_Number):
    """
    Abstract methods from numbers.Complex
    """
    def __add__(self, other):
        return self.result_type_class(self._data.__add__(other))

    def __radd__(self, other):
        return self.classtype(self._data.__radd__(other))

    def __neg__(self):
        return self.result_type_class(self._data.__neg__())

    def __pos__(self):
        return self.result_type_class(self._data.__pos__())

    def __mul__(self, other):
        return self.result_type_class(self._data.__mul__(other))

    def __rmul__(self, other):
        return self.result_type_class(self._data.__rmul__(other))

    def __truediv__(self, other):
        return self.result_type_class(self._data.__truediv__(other))

    def __rtruediv__(self, other):
        return self.result_type_class(self._data.__rtruediv__(other))

    def __rpow__(self, base):
        return self.result_type_class(self._data.__rpow__(exponent))

    def __abs__(self):
        return self.result_type_class(self._data.__abs__())

    def __eq__(self, other):
        return self._data.__eq__(other)

class _Real(_Complex):
    """
    Abstract methods from numbers.Real
    """
    def __trunc__(self):
        return self.result_type_class(self._data.__trunc__())

    def __floor__(self):
        return self.result_type_class(self._data.__floor__())

    def __ceil__(self):
        return self.result_type_class(self._data.__ceil__())

    def __round__(self, ndigits=None):
        return self.result_type_class(self._data.__round__(ndigits=ndigits))

    def __floordiv__(self, other):
        return self.result_type_class(self._data.__floordiv__(other))

    def __rfloordiv__(self, other):
        return self.result_type_class(self._data.__rfloordiv__(other))
        
    def __mod__(self, other):
        return self.result_type_class(self._data.__mod__(other))
        
    def __rmod__(self, other):
        return self.result_type_class(self._data.__rmod__(other))
        
    def __lt__(self, other):
        return self._data.__lt__(other)
        
    def __le__(self, other):
        return self._data.__le__(other)

class IntegralType(_Real):        
    """
    Abstract methods from numbers.Integral
    """
    def __int__(self):
        return self._data.__int__()

    def __pow__(self, exponent, modulus=None):
        if modulus:
            return self.result_type_class(self._data.__pow__(exponent, modulus=modulus))
        else:
            return self.result_type_class(self._data.__pow__(exponent))

    def __lshift__(self, other):
        return self.result_type_class(self._data.__lshift__(other))

    def __rlshift__(self, other):
        return self.result_type_class(self._data.__rlshift__(other))

    def __rshift__(self, other):
        return self.result_type_class(self._data.__rshift__(other))

    def __rrshift__(self, other):
        return self.result_type_class(self._data.__rrshift__(other))

    def __and__(self, other):
        return self.result_type_class(self._data.__and__(other))

    def __rand__(self, other):
        return self.result_type_class(self._data.__rand__(other))

    def __xor__(self, other):
        return self.result_type_class(self._data.__xor__(other))

    def __rxor__(self, other):
        return self.result_type_class(self._data.__rxor__(other))

    def __or__(self, other):
        return self.result_type_class(self._data.__or__(other))

    def __ror__(self, other):
        return self.result_type_class(self._data.__ror__(other))

    def __invert__(self):
        return self.result_type_class(self._data.__invert__())

"""
Int https://core.telegram.org/type/int
"""
class Int(IntegralType):
    _struct = struct.Struct('!i')

    @property
    def internal_data_type(self):
        return int

    @property
    def result_type_class(self):
        return type(self)

    def serialize(self):
        return Int._struct.pack(self._data)

Int.register(int)

"""
Long https://core.telegram.org/type/long
"""
class Long(IntegralType):
    _struct = struct.Struct('!q')

    @property
    def internal_data_type(self):
        return int

    @property
    def result_type_class(self):
        return type(self)

    def serialize(obj):
        return Long._struct.pack(self._data)

Long.register(int)

"""
Bool https://core.telegram.org/type/bool
"""
class Bool(IntegralType):
    _struct = struct.Struct('!q')

    @property
    def internal_data_type(self):
        return bool

    @property
    def result_type_class(self):
        return type(self)

    def serialize(obj):
        return Bool._struct.pack(self._data)

Bool.register(bool)

"""
"""
class Vector(TLType):
    def __init__(self, vector_type):
        if not isinstance(vector_type, type):
            raise TypeError('vector_type must be a type')
        self._type = vector_type
        self._data = []

    def serialize(self):
        result = b''
        for d in self._data:
            result += d.serialize()
        return result