# -*- coding: utf-8 -*-
from __future__ import (print_function, division, absolute_import, unicode_literals, )

import __builtin__

from six import PY2
if PY2:
    from itertools import (
        ifilterfalse as filterfalse,
        takewhile,
        islice,
        dropwhile,
        izip as zip,
    )
else:
    from itertools import (
        filterfalse,
        takewhile,
        islice,
        dropwhile,
    )

from .base import VariantType
from ..utils import compose


class NoContentStreamError(Exception):
    pass


class LessContentStreamError(Exception):
    pass


class NotIterableError(Exception):
    pass


class Stream(VariantType):
    __slots__ = ('value', 'xs', )

    def __init__(self, xs=None):
        self.xs = xs
        super(Stream, self).__init__(lambda ys: ys)

    def bind(self, l_T_to_l_U):
        return compose(self.value, l_T_to_l_U)

    def map(self, l_T_to_l_U):
        self.value = compose(self.value, l_T_to_l_U)
        return self

    def __lshift__(self, xs):
        return self.value(xs)

    def lookup_(self, xs=None):
        if self.xs and xs:
            raise TypeError('Too many arguments')

        if self.xs:
            return self.value(self.xs)
        return self.value(xs)

    def __call__(self, xs=None):
        return self.lookup_(xs)


class Empty(Stream):
    __slots__ = ('value', 'xs', 'error', )

    def __init__(self, error=None):
        self.error = error
        super(Stream, self).__init__(None)

    def map(self, l_T_to_l_U):
        return self

    def __lshift__(self, xs):
        return self

    def __call__(self, xs=None):
        return self

    def __repr__(self):
        return super(Stream, self).__repr__() + " reason => " + str(type(self.error))


# class OrderedStream(Stream):
#     def __init__(self, xs, key_from_x):
#         self.xs = xs
#         self.key_from_x = key_from_x
#         return
#
#     def __iter__(self):
#         xsd = self.xs | to_list()
#         xsd.sort(key = self.key_from_x)
#         for x in xsd:
#             yield x
#
#


def dispatch_stream(original_query):
    func_name = original_query.func_name

    # TODO: should be methodtype?
    # TODO: should support MethodComposer?
    def _method_chaining_base(self, *args, **kw):
        if isinstance(self, Empty):
            return self
        return self.map(lambda xs: original_query(xs, *args, **kw))
    setattr(Stream, func_name, _method_chaining_base)


@dispatch_stream
def select(xs, y_from_x):
    for x in xs:
        yield y_from_x(x)


@dispatch_stream
def where(xs, predicate):
    '''
    >>> range(10) | where(lambda x: x % 2 == 0) | to_tuple()
    (0, 2, 4, 6, 8)
    '''
    for x in xs:
        if predicate(x):
            yield x


@dispatch_stream
def aggregate(xs, seed, a_from_a_x, y_from_a=lambda a: a):
    '''
    >>> import string
    >>> u = string.upper
    >>> cat = lambda a, x: a + ':' + x
    >>> ['a', 'b', 'c'] | aggregate('z', cat)
    'z:a:b:c'
    >>> ['a'] | aggregate('z', cat)
    'z:a'
    >>> [] | aggregate('z', cat)
    'z'
    >>> ['a', 'b', 'c'] | aggregate('z', cat, u)
    'Z:A:B:C'
    >>> ['a'] | aggregate('z', cat, u)
    'Z:A'
    >>> [] | aggregate('z', cat, u)
    'Z'
    '''
    a = seed
    for x in xs:
        a = a_from_a_x(a, x)
    return y_from_a(a)


@dispatch_stream
def aggregate1(xs, a_from_a_x):
    # TODO: Think about more proper name.
    '''
    >>> cat = lambda a, x: a + ':' + x
    >>> ['a', 'b', 'c'] | aggregate1(cat)
    'a:b:c'
    >>> ['a'] | aggregate1(cat)
    'a'
    >>> [] | aggregate1(cat)
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain some element
    '''
    xsd = (x for x in xs)
    try:
        a = xsd.next()
    except StopIteration:
        raise ValueError('Sequence must contain some element')

    return xsd | aggregate(a, a_from_a_x)


@dispatch_stream
def all(xs, predicate):
    '''
    >>> [1, 2, 3] | all(lambda x: isinstance(x, int))
    True
    >>> [1, 'b', 3] | all(lambda x: isinstance(x, int))
    False
    >>> ['a', 'b', 'c'] | all(lambda x: isinstance(x, int))
    False
    >>> [] | all(lambda x: isinstance(x, int))
    True
    '''
    for x in xs:
        if not predicate(x):
            return False
    return True


@dispatch_stream
def any(xs, predicate=lambda x: True):
    return __builtin__.any(x for x in xs if predicate(x))


@dispatch_stream
def average(xs, number_from_x=lambda x: x):
    '''
    >>> [1, 2, 3] | average()
    2
    >>> ['a', 'ab', 'abc'] | average(lambda x: len(x))
    2
    >>> [] | average()
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain some element
    '''
    sum = 0
    count = 0
    for x in xs:
        sum += number_from_x(x)
        count += 1
    if count == 0:
        raise ValueError('Sequence must contain some element')
    return sum / count


@dispatch_stream
def concat(xs, ys):
    '''
    >>> xs = repeat(1, 3)
    >>> ys = repeat(2, 3)
    >>> xs | concat(ys) | to_tuple()
    (1, 1, 1, 2, 2, 2)
    '''
    for x in xs:
        yield x
    for y in ys:
        yield y


@dispatch_stream
def contains(xs, the_x):
    '''
    >>> [1, 2, 3] | contains(2)
    True
    >>> [1, 2, 3] | contains('2')
    False
    >>> [] | contains(2)
    False
    '''
    return xs | any(lambda x: x == the_x)


@dispatch_stream
def count(xs, predicate=lambda x: True):
    '''
    >>> [1, 2, 3] | count()
    3
    >>> range(10) | where(lambda x: x % 2 == 0) | count()
    5
    >>> [] | count()
    0
    '''
    return __builtins__.sum(1 for x in xs | where(predicate))


@dispatch_stream
def default_if_empty(xs, default_value):
    '''
    >>> [1, 2, 3] | default_if_empty('x') | to_tuple()
    (1, 2, 3)
    >>> [] | default_if_empty('x') | to_tuple()
    ('x',)
    '''
    has_value = False
    for x in xs:
        has_value = True
        yield x
    if not has_value:
        yield default_value


@dispatch_stream
def distinct(xs):
    '''
    >>> [1, 2, 3] | distinct() | to_tuple()
    (1, 2, 3)
    >>> [1, 2, 3, 1, 2, 3] | distinct() | to_tuple()
    (1, 2, 3)
    '''
    seen = set()
    seen_add = seen.add
    for element in filterfalse(seen.__contains__, xs):
        seen_add(element)
        yield element


@dispatch_stream
def element_at(xs, index):
    '''
    >>> Stream([0, 1, 2, 3]).element_at(2).lookup_()
    2
    >>> Stream([0, 1, 2, 3]).element_at(10).lookup_()
    Empty: < None > reason => <class 'masala.datatype.stream.LessContentStreamError'>
    '''
    for i, x in enumerate(xs):
        if i == index:
            return x
    return Empty(LessContentStreamError())


@dispatch_stream
def element_at_or_default(xs, index, default_value):
    '''
    >>> Stream([0, 1, 2, 3]).element_at_or_default(2, 'hi').lookup_()
    2
    >>> Stream([0, 1, 2, 3]).element_at_or_default(4, 'hi').lookup_()
    'hi'
    '''
    for i, x in enumerate(xs):
        if i == index:
            return x
    return default_value


def empty():
    '''
    >>> empty() | any()
    False
    >>> empty() | count()
    0
    '''
    return ()


@dispatch_stream
def except_from(xs, xsd):
    '''
    >>> [0, 1, 2, 3] | except_from((1, 2)) | to_tuple()
    (0, 3)
    >>> # TODO: Is this behavior same as .NET Framework?
    >>> [0, 1, 0, 1, 2, 3] | except_from((1, 2, 1)) | to_tuple()
    (0, 0, 3)
    >>> [0, 1, 2, 3] | except_from(()) | to_tuple()
    (0, 1, 2, 3)
    >>> [0, 1, 2, 3] | except_from((4, 5, 6)) | to_tuple()
    (0, 1, 2, 3)
    '''
    for x in xs:
        if xsd | contains(x):
            pass
        else:
            yield x


@dispatch_stream
def first(xs, predicate=lambda x: True):
    for x in xs:
        if predicate(x):
            return x
    return Empty(NoContentStreamError())


@dispatch_stream
def first_or_default(xs, default_value, predicate=lambda x: True):
    for x in xs:
        if predicate(x):
            return x
    return default_value

# TODO: GroupBy

# TODO: Intersect

# TODO: Join


@dispatch_stream
def last(xs, predicate=lambda x: True):
    '''
    >>> [0, 1, 2, 3] | last()
    3
    >>> [0, 1, 2, 3] | last(lambda x: x % 2 == 0)
    2
    >>> [] | last()
    Traceback (most recent call last):
        ...
    ValueError: Sequence must contain some element
    '''
    sentinel = []
    result = xs | last_or_default(sentinel, predicate)
    if result is sentinel:
        raise ValueError('Sequence must contain some element')
    else:
        return result


@dispatch_stream
def last_or_default(xs, default_value, predicate=lambda x: True):
    '''
    >>> [0, 1, 2, 3] | last_or_default('hi')
    3
    >>> [] | last_or_default('hi')
    'hi'
    >>> [0, 1, 2, 3] | last_or_default('hi', lambda x: x % 2 == 0)
    2
    >>> [1, 3, 5, 7] | last_or_default('hi', lambda x: x % 2 == 0)
    'hi'
    >>> [] | last_or_default('hi', lambda x: x % 2 == 0)
    'hi'
    '''
    sentinel = []
    last_value = sentinel
    for x in xs:
        if predicate(x):
            last_value = x
    if last_value is sentinel:
        return default_value
    else:
        return last_value


@dispatch_stream
def max(xs, y_from_x=lambda x: x):
    '''
    >>> range(10) | max()
    9
    >>> range(10) | max(lambda x: -x)
    0
    '''
    return __builtins__.max(y_from_x(x) for x in xs)


@dispatch_stream
def min(xs, y_from_x=lambda x: x):
    '''
    >>> range(10) | min()
    0
    >>> range(10) | min(lambda x: -x)
    -9
    '''
    return __builtins__.min(y_from_x(x) for x in xs)


# @dispatch_stream
# def order_by(xs, key_from_x):
#     '''
#     >>> range(10) | order_by(lambda x: -x) | to_tuple()
#     (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
#     '''
#     return OrderdStream(xs, key_from_x)

# TODO: OrderByDescending


@dispatch_stream
def repeat(x, n=None):
    '''
    >>> repeat(1, 3) | to_tuple()
    (1, 1, 1)
    >>> repeat(1) | take(5) | to_tuple()
    (1, 1, 1, 1, 1)
    '''
    if n is None:
        while True:
            yield x
    else:
        for i in range(n):
            yield x


@dispatch_stream
def reverse(xs):
    return reversed(list(xs))


@dispatch_stream
def select_many(xs, ys_from_x):
    '''
    >>> [1, 2, 3] | select_many(lambda x: [x] * x) | to_tuple()
    (1, 2, 2, 3, 3, 3)
    '''
    for x in xs:
        for y in ys_from_x(x):
            yield y


@dispatch_stream
def select_many_with_index(xs, ys_from_x_i):
    '''
    >>> [1, 2, 3] | select_many_with_index(lambda x, i: [x] * i) | to_tuple()
    (2, 3, 3)
    '''
    for i, x in enumerate(xs):
        for y in ys_from_x_i(x, i):
            yield y


@dispatch_stream
def select_with_index(xs, y_from_x_i):
    '''
    >>> [3, 2, 1] | select_with_index(lambda x, i: x * i) | to_tuple()
    (0, 2, 2)
    '''
    for i, x in enumerate(xs):
        yield y_from_x_i(x, i)

# TODO: SequenceEqual


@dispatch_stream
def single(xs, predicate=lambda x: True):
    '''
    >>> [9] | single()
    9
    >>> [] | single()
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    >>> range(10) | single()
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    >>> [1, 9, 1] | single(lambda x: 1 < x)
    9
    >>> [] | single()
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    >>> range(10) | single()
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    '''
    sentinel = []
    result = xs | single_or_default(sentinel, predicate)
    if result is sentinel:
        raise ValueError('Sequence must contain only one element')
    else:
        return result


@dispatch_stream
def single_or_default(xs, default_value, predicate=lambda x: True):
    '''
    >>> [9] | single_or_default('hi')
    9
    >>> [] | single_or_default('hi')
    'hi'
    >>> range(10) | single_or_default('hi')
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    >>> [1, 9, 1] | single_or_default('hi', lambda x: 1 < x)
    9
    >>> [] | single_or_default('hi')
    'hi'
    >>> range(10) | single_or_default('hi')
    Traceback (most recent call last):
      ...
    ValueError: Sequence must contain only one element
    '''
    sentinel = []
    the_value = sentinel
    for x in xs | where(predicate):
        if the_value is sentinel:
            the_value = x
        else:
            raise ValueError('Sequence must contain only one element')
    if the_value is sentinel:
        return default_value
    else:
        return the_value


@dispatch_stream
def skip(xs, n):
    '''
    >>> range(10) | skip(5) | to_tuple()
    (5, 6, 7, 8, 9)
    '''
    return islice(xs, n, None)


@dispatch_stream
def skip_while(xs, predicate):
    '''
    >>> [1, 3, 5, 7, 5, 3, 1] | skip_while(lambda x: x < 5) | to_tuple()
    (5, 7, 5, 3, 1)
    '''
    return dropwhile(predicate, xs)


@dispatch_stream
def skip_while_with_index(xs, predicate_with_index):
    '''
    >>> [1, 3, 5, 7] | skip_while_with_index(lambda x, i: x + i < 5) | to_tuple()
    (5, 7)
    '''
    skipping = True
    for i, x in enumerate(xs):
        if skipping and predicate_with_index(x, i):
            pass
        else:
            skipping = False
            yield x


@dispatch_stream
def sum(xs, y_from_x=lambda x: x):
    '''
    >>> range(10) | sum()
    45
    >>> range(10) | sum(lambda x: -x)
    -45
    '''
    return __builtin__.sum(y_from_x(x) for x in xs)


@dispatch_stream
def take(xs, n):
    '''
    >>> range(10) | take(5) | to_tuple()
    (0, 1, 2, 3, 4)
    '''
    return islice(xs, n)


@dispatch_stream
def take_while(xs, predicate):
    '''
    >>> [1, 3, 5, 7, 5, 3, 1] | take_while(lambda x: x < 5) | to_tuple()
    (1, 3)
    '''
    return takewhile(predicate, xs)


@dispatch_stream
def take_while_with_index(xs, predicate_with_index):
    '''
    >>> [1, 3, 5, 7] | take_while_with_index(lambda x, i: x + i < 5) | to_tuple()
    (1, 3)
    '''
    for i, x in enumerate(xs):
        if predicate_with_index(x, i):
            yield x
        else:
            break


# @dispatch_stream
# def then_by(ordered_xs, key_from_x):
#     '''
#     >>> (range(10)
#     ...  | order_by(lambda x: x % 2)
#     ...  | to_tuple())
#     (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)
#     >>> (range(10)
#     ...  | order_by(lambda x: x % 2)
#     ...  | order_by(lambda x: -x)
#     ...  | to_tuple())
#     (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
#     >>> (range(10)
#     ...  | order_by(lambda x: x % 2)
#     ...  | then_by(lambda x: -x)
#     ...  | to_tuple())
#     (8, 6, 4, 2, 0, 9, 7, 5, 3, 1)
#     >>> (range(10)                         # (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
#     ...  | order_by(lambda x: x % 2)       # (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)
#     ...                                    #  -------------  -------------
#     ...  | then_by(lambda x: x % 4 != 0)   # (0, 4, 8, 2, 6, 1, 3, 5, 7, 9)
#     ...                                    #  -------  ----  -------------
#     ...  | then_by(lambda x: -x)
#     ...  | to_tuple())
#     (8, 4, 0, 6, 2, 9, 7, 5, 3, 1)
#     '''
#     if isinstance(ordered_xs, OrderdStream):
#         return OrderdStream(ordered_xs.xs,
#                                lambda x: (ordered_xs.key_from_x(x), key_from_x(x)))
#     else:
#         raise ValueError('Sequence must be sorted with order_by')

# TODO: ThenByDescending


@dispatch_stream
def to_dict(xs, key_from_x, value_from_x=lambda x: x):
    '''
    >>> d = ['apple', 'banana', 'cherry'] | to_dict(lambda x: x[0])
    >>> d['a']
    'apple'
    >>> d['b']
    'banana'
    >>> d['c']
    'cherry'
    >>> len(d.keys())
    3
    >>> d = ['ada', 'basic', 'cl'] | to_dict(lambda x: x[0], lambda x: len(x))
    >>> d['a']
    3
    >>> d['b']
    5
    >>> d['c']
    2
    >>> len(d.keys())
    3
    >>> d = ['ada', 'basic', 'csp'] | to_dict(lambda x: len(x), lambda x: x)
    Traceback (most recent call last):
      ...
    LookupError: Key 3 (for 'csp') is duplicate
    '''
    d = {}
    for x in xs:
        k = key_from_x(x)
        v = value_from_x(x)
        if k in d:
            raise LookupError('Key %r (for %r) is duplicate' % (k, x))
        else:
            d[k] = v
    return d


@dispatch_stream
def to_list(xs):
    '''
    >>> Stream(xrange(10)).to_list()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> Stream(True).to_list()
    Empty: < None > reason => <class 'masala.datatype.stream.NotIterableError'>
    '''
    try:
        return list(xs)
    except TypeError as e:
        return Empty(NotIterableError(e.message))


@dispatch_stream
def to_lookup(xs, key_from_x, value_from_x=lambda x: x):
    '''
    >>> d = ['ada', 'awk', 'bash', 'bcpl', 'c'] | to_lookup(lambda x: x[0])
    >>> d['a'] | to_tuple()
    ('ada', 'awk')
    >>> d['b'] | to_tuple()
    ('bash', 'bcpl')
    >>> d['c'] | to_tuple()
    ('c',)
    >>> len(d.keys())
    3
    >>> d = ['ada', 'awk', 'bash', 'bcpl', 'c'] | to_lookup(lambda x: x[0], len)
    >>> d['a'] | to_tuple()
    (3, 3)
    >>> d['b'] | to_tuple()
    (4, 4)
    >>> d['c'] | to_tuple()
    (1,)
    >>> len(d.keys())
    3
    '''
    d = {}
    for x in xs:
        k = key_from_x(x)
        v = value_from_x(x)
        if k in d:
            d[k].append(v)
        else:
            d[k] = [v]
    return d


@dispatch_stream
def to_set(xs):
    '''
    >>> range(10) | to_set()
    set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    '''
    return set(xs)


@dispatch_stream
def to_tuple(xs):
    '''
    >>> range(10) | to_tuple()
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
    '''
    return tuple(xs)


@dispatch_stream
def union(xs, ys):
    '''
    >>> xs = list(repeat(1, 3))
    >>> xs.append(3)
    >>> xs.append(4)
    >>> ys = list(repeat(2, 3))
    >>> ys.append(3)
    >>> ys.append(5)
    >>> xs | union(ys) | to_tuple()
    (1, 3, 4, 2, 5)
    '''
    return xs | concat(ys) | distinct()



@dispatch_stream
def where_with_index(xs, predicate_with_index):
    '''
    >>> [1, 3, 5, 7] | where_with_index(lambda x, i: i % 2 == 0) | to_tuple()
    (1, 5)
    '''
    for i, x in enumerate(xs):
        if predicate_with_index(x, i):
            yield x


@dispatch_stream
def zip(xs, ys, xy_to_z=lambda xy: xy):
    '''
    >>> [1, 2, 3] | zip('abcd', lambda xy: str(xy[0]) + ':' + xy[1]) | to_tuple()
    ('1:a', '2:b', '3:c')
    >>> range(5) | zip('abcd') | to_tuple()
    ((0, 'a'), (1, 'b'), (2, 'c'), (3, 'd'))
    '''
    return (xy_to_z(xy) for xy in zip(xs, ys))


@dispatch_stream
def foreach(xs, action):
    '''
    >>> def printfunc(x): print x
    >>> range(3) | foreach(printfunc)
    0
    1
    2
    '''
    for x in xs:
        action(x)


@dispatch_stream
def foreach_with_index(xs, action_with_index):
    '''
    >>> def printfunc_with_index(x, i): print "ind->" + str(i) + " ran->" + str(x)
    >>> ['one', 'two', 'three'] | foreach_with_index(printfunc_with_index)
    ind->0 ran->one
    ind->1 ran->two
    ind->2 ran->three
    '''
    for i, x in enumerate(xs):
        action_with_index(x, i)


if __name__ == '__main__':
    import doctest
    doctest.testmod()

# __END__
