# Copyright 2020 MIT Probabilistic Computing Project.
# See LICENSE.txt

from functools import reduce
from itertools import combinations

from sympy import Intersection

from .sym_util import EmptySet

from .transforms import EventAnd
from .transforms import EventBasic
from .transforms import EventOr

def dnf_factor(event, lookup=None):
    # Given an event (in DNF) and a dictionary lookup mapping symbols
    # to integers, this function returns a list R of dictionaries
    # R[i][j] is a conjunction events in the i-th DNF clause whose symbols
    # are assigned to integer j in the lookup dictionary.
    #
    # For example, if e is any predicate
    # event = (e(X0) & e(X1) & ~e(X2)) | (~e(X1) & e(X2) & e(X3) & e(X4)))
    # lookup = {X0: 0, X1: 1, X2: 0, X3: 1, X4: 2}
    # The output is
    # R = [
    #   { // First clause
    #       0: e(X0) & ~e(X2),
    #       1: e(X1)},
    #   { // Second clause
    #       0: e(X2),
    #       1: ~e(X1) & e(X3)},
    #       2: e(X4)},
    # ]
    if lookup is None:
        lookup = {s:s for s in event.symbols()}

    if isinstance(event, EventBasic):
        # Literal.
        symbols = event.symbols()
        assert len(symbols) == 1
        key = lookup[symbols[0]]
        return [{key: event}]

    if isinstance(event, EventAnd):
        # Conjunction.
        assert all(isinstance(e, EventBasic) for e in event.subexprs)
        mappings = [dnf_factor(e, lookup) for e in event.subexprs]
        events = {}
        for mapping in mappings:
            assert len(mapping) == 1
            [(key, ev)] = mapping[0].items()
            if key not in events:
                events[key] = ev
            else:
                events[key] &= ev
        return [events]

    if isinstance(event, EventOr):
        # Disjunction.
        assert all(isinstance(e, (EventAnd, EventBasic)) for e in event.subexprs)
        mappings = [dnf_factor(e, lookup) for e in event.subexprs]
        events = [None] * len(mappings)
        for i, mapping in enumerate(mappings):
            events[i] = {}
            for key, ev in mapping[0].items():
                events[i][key] = ev
        return events

    assert False, 'Invalid DNF event: %s' % (event,)

def dnf_normalize(event):
    # Given an arbitrary event, rewrite in terms of only Identity by
    # solving the subexpressions and return the resulting DNF formula,
    # or None if all solutions evaluate to EmptySet.
    event_dnf = event.to_dnf()
    event_factor = dnf_factor(event_dnf)
    solutions = list(filter(lambda x: all(y[1] is not EmptySet for y in x), [
        [(symbol, ev.solve()) for symbol, ev in clause.items()]
        for clause in event_factor
    ]))
    if not solutions:
        return None
    conjunctions = set([
        reduce(lambda x, e: x & e, [(symbol << S) for symbol, S in clause])
        for clause in solutions
    ])
    disjunctions = reduce(lambda x, e: x|e, conjunctions)
    return disjunctions.to_dnf()

def dnf_non_disjoint_clauses(event):
    # Given an event in DNF, returns a dictionary R
    # such that R[j] = [i | i < j and event[i] intersects event[j]]
    event_factor = dnf_factor(event)
    solutions = [
        {symbol: ev.solve() for symbol, ev in clause.items()}
        for clause in event_factor
    ]

    n_clauses = len(event_factor)
    overlap_dict = {}
    for i, j in combinations(range(n_clauses), 2):
        # Exit if any symbol in i does not intersect a symbol in j.
        intersections = {
            symbol: Intersection(solutions[i][symbol], solutions[j][symbol])
                if (symbol in solutions[j]) else solutions[i][symbol]
            for symbol in solutions[i]
        }
        if any(x is EmptySet for x in intersections.values()):
            continue
        # Exit if any symbol in j is EmptySet.
        if any(solutions[j] is EmptySet
                for symbol in solutions[j] if symbol not in solutions[i]):
            continue
        # All symbols intersect, so clauses overlap.
        if j not in overlap_dict:
            overlap_dict[j] = []
        overlap_dict[j].append(i)

    return overlap_dict

def dnf_to_disjoint_union(event):
    # Given an arbitrary event, returns an event in DNF where all the
    # clauses are disjoint from one another, by recursively solving the
    # identity E = (A or B or C) = (A) or (B and ~A) or (C and ~A and ~B).
    event_dnf = event.to_dnf()
    # Base case.
    if isinstance(event_dnf, (EventBasic, EventAnd)):
        return event_dnf
    # Find indexes of pairs of clauses that overlap.
    overlap_dict = dnf_non_disjoint_clauses(event_dnf)
    if not overlap_dict:
        return event_dnf
    # Create the cascading negated clauses.
    n_clauses = len(event_dnf.subexprs)
    clauses_disjoint = [
        reduce(
            lambda state, event: state & ~event,
            (event_dnf.subexprs[j] for j in overlap_dict.get(i, [])),
            event_dnf.subexprs[i])
        for i in range(n_clauses)
    ]
    # Recursively find the solutions for each clause.
    solutions = [dnf_to_disjoint_union(clause) for clause in clauses_disjoint]
    # Return the merged solution.
    return reduce(lambda a, b: a|b, solutions)
