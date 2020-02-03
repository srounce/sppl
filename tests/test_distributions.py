# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

from fractions import Fraction
from math import log

import pytest


import numpy
import scipy.stats
import sympy

from sum_product_dsl.distributions import MixtureDistribution
from sum_product_dsl.distributions import NominalDistribution
from sum_product_dsl.distributions import NumericDistribution
from sum_product_dsl.transforms import Identity

from sum_product_dsl.math_util import allclose
from sum_product_dsl.math_util import isinf_neg
from sum_product_dsl.math_util import logsumexp
from sum_product_dsl.sym_util import Reals
from sum_product_dsl.sym_util import RealsPos

rng = numpy.random.RandomState(1)

def test_nominal_distribution():
    X = Identity('X')
    probs = {'a': Fraction(1, 5), 'b': Fraction(1, 5), 'c': Fraction(3, 5)}
    dist = NominalDistribution(X, probs)
    assert dist.logprob(X << {'a'}) == sympy.log(Fraction(1, 5))
    assert dist.logprob(X << {'b'}) == sympy.log(Fraction(1, 5))
    assert dist.logprob(X << {'a', 'c'}) == sympy.log(Fraction(4, 5))
    assert dist.logprob((X << {'a'}) & ~(X << {'b'})) == sympy.log(Fraction(1, 5))
    assert dist.logprob((X << {'a', 'b'}) & ~(X << {'b'})) == sympy.log(Fraction(1, 5))
    assert dist.logprob((X << {'d'})) == -float('inf')
    assert dist.logprob((X << ())) == -float('inf')

    samples = dist.sample(100, rng)
    assert all(x in dist.support for x in samples)

    predicate = (X << {'a', 'b'}) | X << {'c'}
    samples = dist.sample_expr(predicate, 100, rng)
    assert all(samples)

    predicate = (~(X << {'a', 'b'})) & ~(X << {'c'})
    samples = dist.sample_expr(predicate, 100, rng)
    assert not any(samples)

    func = lambda X: 1 if X in {'a'} else None
    samples = dist.sample_func(func, 100, rng)
    assert sum(1 for s in samples if s == 1) > 12
    assert sum(1 for s in samples if s is None) > 70

    with pytest.raises(ValueError):
        dist.sample_func(lambda Y: Y, 100, rng)

    dist_condition = dist.condition(X<<{'a', 'b'})
    assert dist_condition.support == {'a', 'b', 'c'}
    assert dist_condition.logprob(X << {'a'}) \
        == dist_condition.logprob(X << {'b'}) \
        == -sympy.log(2)
    assert dist_condition.logprob(X << {'c'}) == -float('inf')

def test_numeric_distribution_normal():
    X = Identity('X')
    probs = scipy.stats.norm(loc=0, scale=1)
    dist = NumericDistribution(X, probs, Reals)

    assert allclose(dist.logprob(X > 0), -log(2))
    assert allclose(dist.logprob(abs(X) < 2), log(probs.cdf(2) - probs.cdf(-2)))

    assert allclose(dist.logprob(X**2 > 0), 0)
    assert allclose(dist.logprob(abs(X) > 0), 0)
    assert allclose(dist.logprob(~(X << {1})), 0)

    assert isinf_neg(dist.logprob(X**2 - X + 10 < 0))
    assert isinf_neg(dist.logprob(abs(X) < 0))
    assert isinf_neg(dist.logprob(X << {1}))

    dist.sample_expr(X**2, 1, rng)
    dist.sample_expr(abs(X)+X**2, 1, rng)
    dist.sample_func(lambda X: X**2 if X > 0 else X**3, 100, rng)

    dist_condition_a = dist.condition((X < 2) | (X > 10))
    samples = dist_condition_a.sample(100, rng)
    assert all(s < 2 for s in samples)

    dist_condition_b = dist.condition((X < -10) | (X > 10))
    assert isinstance(dist_condition_b, MixtureDistribution)
    assert allclose(dist_condition_b.weights[0], -log(2))
    assert allclose(dist_condition_b.weights[0], dist_condition_b.weights[1])

    for event in [(X<-10), (X>3)]:
        dist_condition_c = dist.condition(event)
        assert isinstance(dist_condition_c, NumericDistribution)
        assert isinf_neg(dist_condition_c.logprob((-1 < X) < 1))
        samples = dist_condition_c.sample(100, rng)
        assert all(s in event.values for s in samples)

    with pytest.raises(ValueError):
        dist.condition((X > 1) & (X < 1))

    with pytest.raises(ValueError):
        dist.condition(X << {1})

    with pytest.raises(ValueError):
        dist.sample_func(lambda Z: Z**2, 1, rng)

def test_mixture_distribution_normal_gamma():
    X = Identity('X')
    weights = [
        log(Fraction(2, 3)),
        log(Fraction(1, 3))
    ]
    dist = MixtureDistribution([
            NumericDistribution(X, scipy.stats.norm(loc=0, scale=1), Reals),
            NumericDistribution(X, scipy.stats.gamma(loc=0, a=1), RealsPos),
        ], weights)

    assert dist.logprob(X > 0) == logsumexp([
        dist.weights[0] + dist.distributions[0].logprob(X > 0),
        dist.weights[1] + dist.distributions[1].logprob(X > 0),
    ])

    dist_condition = dist.condition(X < 0)
    assert isinstance(dist_condition, NumericDistribution)
    assert dist_condition.conditioned
    assert dist_condition.logprob(X < 0) == 0

    assert dist.logprob(X < 0) == logsumexp([
        dist.weights[0] + dist.distributions[0].logprob(X < 0),
        dist.weights[1] + dist.distributions[1].logprob(X < 0),
    ])
