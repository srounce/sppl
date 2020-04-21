# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

from math import log

import numpy
import pytest

from spn.distributions import norm
from spn.math_util import allclose
from spn.spn import Memo
from spn.transforms import Identity

prng = numpy.random.RandomState(1)

@pytest.mark.parametrize('memo', [Memo({}, {}), None])
def test_mutual_information_four_clusters(memo):
    X = Identity('X')
    Y = Identity('Y')
    spn \
        = 0.25*(X >> norm(loc=0, scale=0.5) & Y >> norm(loc=0, scale=0.5)) \
        | 0.25*(X >> norm(loc=5, scale=0.5) & Y >> norm(loc=0, scale=0.5)) \
        | 0.25*(X >> norm(loc=0, scale=0.5) & Y >> norm(loc=5, scale=0.5)) \
        | 0.25*(X >> norm(loc=5, scale=0.5) & Y >> norm(loc=5, scale=0.5)) \

    samples = spn.sample(100, prng)
    mi = spn.mutual_information(X > 2, Y > 2, memo=memo)
    assert allclose(mi, 0)

    event = ((X>2) & (Y<2) | ((X<2) & (Y>2)))
    spn_condition = spn.condition(event)
    samples = spn_condition.sample(100, prng)
    assert all(event.evaluate(sample) for sample in samples)
    mi = spn_condition.mutual_information(X > 2, Y > 2)
    assert allclose(mi, log(2))
