from snakes.data import MultiSet

def keys(m, v):
    """ Given a MultiSet `m` of key-value pairs (e.g., {('t0', 'p1'), ('t0', 'p2')})
    and a value `v` (e.g., 'p1'),
    it returns a multiset containing the keys associated with the value `v`.
    e.g., pre_pl({('t0', 'p1'), ('t0', 'p2')}, 'p1') = {'t0'}"""
    result = MultiSet([])
    for pair in m:
        if pair[1] == v:
            result.add(pair[0])
    return result

def values(m, k):
    """ Given a MultiSet `m` of key-value pairs (e.g., {('t0', 'p1'), ('t0', 'p2')})
    and an key `k` (e.g., 't0'),
    it returns a multiset containing the values associated with the key `k`.
    e.g., pre_tr({('t0', 'p1'), ('t0', 'p2')}, 't0') = {'p1', 'p2'}"""
    result = MultiSet([])
    for pair in m:
        if pair[0] == k:
            result.add(pair[1])
    return result

def value(m, key):
    """ Given a MultiSet `m` of (key, value) pairs (e.g., {('t0', 'p0'), ('t0', 'p1')}),
    it returns a MultiSet of the values associated with the given `key`.
    e.g., value({('t0', 'p0') * 2, ('t0', 'p1')}, 't0') = {'p0' * 2, 'p1'}"""
    #print('value( ' + str(m) + ', ' + str(key) + ' )')
    result = MultiSet([])
    for pair in m:
            if pair[0] == key:
                result = result + MultiSet([pair[1]])
    #print('  result = ' + str(result))
    return result

def projection(m1, m2):
    """ Given two MultiSets `m1`, `m2` (e.g., {'p0', 'p1'}, {'p0' * 2}),
    it returns a projection of `m1` containing only the elements appearing in `m2`.
    e.g., projection({'p0', 'p1'}, {'p0' * 2}) = {'p0'}"""
    #print('projection( ' + str(m1) + ', ' + str(m2) + ' )')
    result = MultiSet([])
    for e in m1:
        if m2(e)>0:
            result.add([e])
    #print('  result = ' + str(result))
    return result

def existsH(m1, m2):
    """ Given two MultiSets `m1`, `m2` (e.g., {'p0' * 2, 'p1', 'p2'}, {'p0', 'p2'}),
    it returns False if there exists an element in m2 with >= multiplicity. """
    return None

def intersection(m1, m2):
    """ Given two MultiSets `m1`, `m2` (e.g., {'p0' * 2, 'p1', 'p2'}, {'p0', 'p2'}),
    it returns the intersection. e.g., intersection({'p0' *2, 'p1', 'p2'}, {'p0', 'p2'}) = {'p0', 'p2'}"""
    result = MultiSet([])
    for e in set(m1):
        n1 = m1(e)
        n2 = m2(e)
        if n1>0 and n2>0:
            mult = n1
            if n2 < n1:
                mult = n2
            result.add([e] * mult)
    return result

def setMultiplicity(m, e, n):
    """ Given a MultiSet `m` an element `e` and a multiplicity `n`,
    it returns a new MultiSet `m'`, s.t. `m'(e)=n`"""
    result = m.copy()
    if m(e) > 0:
        result.remove(e, m(e))
    result.add(e, n)
    return result

def filterByValue(m, v):
    """ Given a MultiSets `m` of key-value pairs (e.g., {('t0', 'p1') * 2, ('t0', 'p2')})
    and a value `v` (e.g., 'p1'),
    it returns a multiset containing the pairs with the given value `v`.
    e.g., filterByValue({('t0', 'p1'), ('t0', 'p2')}, 'p1') = {('t0', 'p1') * 2}"""
    result = MultiSet([])
    for pair in m:
        if pair[1] == v:
            result.add([pair])
    return result

def filterByKey(m, k):
    """ Given a MultiSets `m` of key-value pairs (e.g., {('t1', 'p1') * 2, ('t0', 'p2')})
    and a key `k` (e.g., 't0'),
    it returns a multiset containing the pairs with the given key `k`.
    e.g., filterByKey({('t0', 'p1'), ('t0', 'p2')}, 't0') = {('t0', 'p2')}"""
    result = MultiSet([])
    for pair in m:
        if pair[0] == k:
            result.add([pair])
    return result
