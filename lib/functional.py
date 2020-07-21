from functools import reduce
from functools import cmp_to_key
from collections.abc import Iterable
import itertools

def xmap(func):
    def run(fl):
        return FuncList(map(func, fl._items))
    return run
def xflatten(func=None):
    def run(fl):
        lst = []
        for x in map(func or (lambda x: x), fl._items):
            if isinstance(x, Iterable):
                lst += x
            else:
                lst.append(x)
        return FuncList(lst)
    return run
def xfilter(func=None):
    def run(fl):
        return FuncList(filter(func or (lambda x: x), fl._items))
    return run
def xreduce(aggregator, initializer=None):
    def run(fl):
        return FuncList(reduce(aggregator, fl._items, initializer))
    return run
def xreduceout(aggregator, initializer=None):
    def run(fl):
        return reduce(aggregator, fl._items, initializer)
    return run
def xconcat(other):
    def run(fl):
        return FuncList(fl._items + other._items)
    return run
def xfirst(func=None, defRet=None):
    def run(fl):
        xfunc = func or (lambda x: x)
        return next((o for o in fl._items if xfunc(o)), defRet)
    return run
def xstopifany(func):
    def run(fl):
        if next((o for o in fl._items if func(o)), None):
            return Fail(fl)
        return fl
    return run
def xproduct(otherlist, func):
    def run(fl):
        return FuncList(map(lambda x: func(x[0], x[1]), itertools.product(fl._items, otherlist)))
    return run

class Fail:
    def __init__(self, l):
        self.items = l

class FuncList:
    def __init__(self, itr):
        self._items = list(itr)
    def pipe(self, *funcs):
        current = self
        for func in funcs:
            current=func(current)
            if isinstance(current, Fail):
                return current.items
        return current
    def foreach(self, func):
        for item in self._items:
            func(item)
    def maxBy(self, keyfunc, default):
        return max(self._items, key=cmp_to_key(keyfunc), default=default)
    def sortedBy(self, keyfunc):
        return sorted(self._items, key=cmp_to_key(keyfunc))
    def tolist(self):
        return list(self._items)