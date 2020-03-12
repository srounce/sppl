# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

import pytest

from sympy import Complement
from sympy import FiniteSet
from sympy import Intersection
from sympy import Interval
from sympy import symbols

from sympy import exp as SymExp
from sympy import log as SymLog

from spn.sym_util import EmptySet
from spn.sym_util import NominalSet
from spn.sym_util import UniversalSet
from spn.sym_util import get_symbols
from spn.sym_util import partition_list_assignments
from spn.sym_util import partition_list_blocks

(X0, X1, X2, X3, X4, X5, X6, X7, X8, X9) = symbols('X:10')

def test_get_symbols():
    syms = get_symbols((X0 > 3) & (X1 < 4))
    assert len(syms) == 2
    assert X0 in syms
    assert X1 in syms

    syms = get_symbols((SymExp(X0) > SymLog(X1)+10) & (X2 < 4))
    assert len(syms) == 3
    assert X0 in syms
    assert X1 in syms
    assert X2 in syms

@pytest.mark.parametrize("a, b, solution", [
    [NominalSet('a'),
        NominalSet('b'),
        EmptySet],
    [NominalSet('a','b', 'c'),
        NominalSet('a'),
        NominalSet('a')],
    [NominalSet('a','b', 'c'),
        Complement(UniversalSet, NominalSet('a')),
        NominalSet('b', 'c')],
    [Interval(0, 1),
        NominalSet('a'),
        EmptySet],
    [Interval(0, 1),
        Complement(UniversalSet, NominalSet('a')),
        Complement(Interval(0, 1), NominalSet('a'))],
    [FiniteSet('a'),
        NominalSet('a'),
        EmptySet],
    [FiniteSet('a'),
        Complement(UniversalSet, NominalSet('a')),
        FiniteSet('a')],
    [FiniteSet(1, 2),
        NominalSet('a'),
        EmptySet],
    [FiniteSet(1, 2),
        Complement(UniversalSet, NominalSet('a')),
        FiniteSet(1, 2)],
])
def test_nominal_set_intersections(a, b, solution):
    assert Intersection(a, b) == solution

@pytest.mark.parametrize('a, b', [
    ([0, 1, 2, 3], {0:0, 1:1, 2:2, 3:3}),
    ([0, 1, 2, 1], {0:0, 1:1, 2:2, 3:1}),
    ([0, 0, 2, 0], {0:0, 1:0, 2:1, 3:0}),
])
def test_partition_list_assignments(a, b):
    solution = partition_list_assignments(a)
    assert solution == b

@pytest.mark.parametrize('a, b', [
    ([0, 1, 2, 3], [[0], [1], [2], [3]]),
    ([0, 1, 2, 1], [[0], [1, 3], [2]]),
    ([0, 0, 2, 0], [[0, 1, 3], [2]]),
])
def test_partition_list_blocks(a, b):
    solution = partition_list_blocks(a)
    assert solution == b
