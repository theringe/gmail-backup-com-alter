# Copyright (C) 2008 Jan Svec and Filip Jurcicek
# 
# YOU USE THIS TOOL ON YOUR OWN RISK!
# 
# email: info@gmail-backup.com
# 
# 
# Disclaimer of Warranty
# ----------------------
# 
# Unless required by applicable law or agreed to in writing, licensor provides
# this tool (and each contributor provides its contributions) on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied, including, without limitation, any warranties or conditions of
# TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR
# PURPOSE. You are solely responsible for determining the appropriateness of
# using this work and assume any risks associated with your exercise of
# permissions under this license. 

import sys
import codecs
from types import StringTypes
from inspect import isroutine

class sym(object):
    def __init__(self, s):
        self.__s = s
    
    def __hash__(self):
        return hash(self.__s)
    
    def __eq__(self, other):
        return self.__s == other

    def __str__(self):
        return str(self.__s)

    def __repr__(self):
        return str(self.__s)

def isstr(obj):
    """Return True if `obj` is string (Unicode or 8-bit)

    :RType: bool
    """
    return isinstance(obj, StringTypes)

def issequence(obj):
    """Return True if `obj` is sequence, but not string

    :RType: bool
    """
    if isstr(obj):
        return False
    else:
        try:
            len(obj)
            return True
        except TypeError:
            return False

def partial(fn, *cargs, **ckwargs):
    def partial_fn(*fargs, **fkwargs):
        d = ckwargs.copy()
        d.update(fkwargs)
        return fn(*(cargs + fargs), **d)
    return partial_fn

def strnumber(obj):
    """Return string representation of `obj`.

    If `obj` is float representing integer number (eg. 2.0), it will return
    integer number (eg. '2'). Otherwise `obj` is converted into string using
    ``str(obj)``.

    :RType: str
    """
    try:
        if int(obj) == float(obj):
            obj = int(obj)
    except (ValueError, TypeError):
        pass
    return str(obj)

def strcomma(seq, comma=', '):
    """Return string representation of sequence `seq`

    Objects of sequence are converted into strings using ``str(obj)``.
    Resulting sequence is then joint using `comma` string. If `comma` is not
    supplied, ', ' will be used.

    :RType: str
    """
    return comma.join(str(o) for o in seq)

def cartezian(*vectors):
    """Compute Cartesian product of passed arguments
    """
    ret = ret_old = [(v,) for v in vectors[0]]
    for vec in vectors[1:]:
        ret = []
        for v in vec:
            for r in ret_old:
                ret.append(r+(v,))
        ret_old = ret
    return ret

def iterslice(sl, length=None):
    """Return xrange() created from slice object `sl`
    """
    if sl.start is None:
        start = 0
    else:
        start = sl.start
    if sl.stop is None:
        if length is None:
            raise ValueError("If slice.stop is None, you must supply length arg.")
        else:
            stop = length
    else:
        stop = sl.stop
    if sl.step is None:
        step = 1
    else:
        step = sl.step
    return xrange(start, stop, step)

def seqIntoDict(seq, format):
    _posOptsDict = {}
    _negativeAfter = sys.maxint
    have_ellipsis = False
    i = 0
    if format.count(Ellipsis) > 1:
        raise ValueError("Ellipsis must be used only once")
    while i < len(format):
        opt_name = format[i]
        if opt_name == Ellipsis:
            have_ellipsis = True
            if i == 0:
                raise ValueError("Ellipsis must be after option name")
            j = -1
            while True:
                opt_name = format[j]
                if opt_name == Ellipsis:
                    break
                _posOptsDict[opt_name] = j
                j -= 1
            if j+1 == 0:
                # slice [i-1:]       != [i-1:0]
                _posOptsDict[format[i-1]] = slice(i-1, None)
            else:
                # slice [i-1:j+1]
                _posOptsDict[format[i-1]] = slice(i-1, j+1)
            # Negative indices can be used if there was enough arguments to
            # fill options preceding Ellipsis
            _negativeAfter = len(_posOptsDict)-1
            break
        _posOptsDict[opt_name] = i
        i += 1

    # Is there enough positional arguments to use negative indices?
    use_negative = ( len(seq) >= _negativeAfter )
    ret = {}

    for opt_name, getter in _posOptsDict.iteritems():
        try:
            if not isinstance(getter, slice):
                # Skip negative indices if there wasn't enough positional
                # arguments
                if getter < 0 and not use_negative:
                    continue
            value = seq[getter]
            if not isinstance(getter, slice):
                ret[opt_name] = value
            elif value:
                ret[opt_name] = value
        except IndexError:
            # Option is not specified
            pass
    return ret

def linspace(start, stop, count):
    if stop < 0:
        (start, stop) = (start+stop, start-stop)
    step = (stop - start) / float(count-1)
    return [start+i*step for i in range(count)]

def linrange(start, stop, step):
    if stop < 0:
        (start, stop) = (start+stop, start-stop)
    count = int(round((stop - start) / step) + 1)
    return [start+i*step for i in range(count)]

unique_value = ['unique_value']

def all_same(seq, default=unique_value):
    for i in seq:
        if default is unique_value:
            default = i
        if i != default:
            return False
    else:
        return True

def _defaultZero():
    return 0

class ADict(dict):
    'Accumulator dictionary'
    def __init__(self, source={}, default=_defaultZero, **kwargs):
        super(ADict, self).__init__(source, **kwargs)
        self._default = default

    def __getitem__(self, key):
        if key not in self:
            ret = self._default()
            try:
                hash(ret)
            except TypeError:
                # Store it
                self[key] = ret
            return ret
        else:
            return super(ADict, self).__getitem__(key)

    def __add__(self, other):
        new = self.__class__(self)
        for key, value in other.iteritems():
            new[key] += value
        return new
    
    def sum(self):
        return sum(self.values())

    def writeToFile(self, fn, key=None, format='%d', encoding='utf-8'):
        fw = codecs.open(fn, 'w', encoding)
        try:
            for key, count in sorted(self.iteritems(), key=key):
                if not issequence(key):
                    key = [key]
                string = u'\t'.join(unicode(i) for i in key)
                value = format % count
                fw.write('%s\t%s\n' % (string, value))
        finally:
            fw.close()

    @classmethod
    def readFromFile(cls, fn, format=int, encoding='utf-8'):
        fr = codecs.open(fn, 'r', encoding)
        try:
            new = cls()
            for line in fr:
                items = line.split()
                value = format(items[-1])
                key = tuple(items[:-1])
                new[key] += value
            return new
        finally:
            fr.close()


