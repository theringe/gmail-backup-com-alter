# -*- coding: utf-8 -*-
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

"""PythonEgg class module
"""
import inspect

from svc.utils import sym

class MetaEgg(type):
    """PythonEgg metaclass
    """
    accessors = {
        'get': ('getter', 0),
        'is': ('getter', 0),
        'set': ('setter', 1),
        'del': ('deller', 0),
    }

    def __init__(cls, name, bases, dict):
        cls.createProperties(dict)
        super(MetaEgg, cls).__init__(name, bases, dict)

    def createProperties(cls, dict):
        props = {}
        for name, object in dict.iteritems():
            type, prop_name = cls.getPropertyDesc(name, object)
            if type is None:
                # No property
                continue
            item = props.setdefault(prop_name,  {})
            if type in item:
                raise ValueError('More than one access method (%r) for property %r' \
                                 % (item[type], prop_name))
            item[type] = name
        for prop_name in props:
            d = cls.getAccessors(prop_name)
            getter = d['getter']
            setter = d['setter']
            deller = d['deller']
            setattr(cls, prop_name, property(getter, setter, deller))

    @classmethod
    def getPropertyDesc(cls, name, object):
        NO_PROPERTY = None, None
        if not inspect.isfunction(object):
            return NO_PROPERTY

        protected = False
        if name[0] == '_':
            protected = True
            name = name[1:]

        for prefix, (type, argcount) in cls.accessors.iteritems():
            obj_argcount = object.func_code.co_argcount - 1  # Minus one for 'self'
            if name.startswith(prefix) and obj_argcount == argcount:
                name = name[len(prefix):]
                if not name:
                    # Skip empty property name
                    continue
                break
        else:
            return NO_PROPERTY

        name = cls._suffixToProperty(name)

        if protected:
            name = '_' + name

        return type, name

    @classmethod
    def _suffixToProperty(cls, suffix):
        """Converts suffix of attribute into property name

        Examples:
            getValue(),     suffix 'Value', property 'value'
            getSomeValue()         'SomeValue'       'someValue'
            getASR()               'ASR'             'ASR'
            getX()                 'X'               'x'
        """
        if len(suffix) == 1:
            # One-char property name
            return suffix.lower()
        elif suffix[0].isupper() and suffix[1].islower():
            # Word property like SomeProperty --> someProperty
            return suffix[0].lower() + suffix[1:]
        else:
            # Word property like ASR --> ASR
            return suffix

    @classmethod
    def _propertyToSuffix(cls, pname):
        """Inversion to _suffixToProperty()
        """
        return pname[0].upper() + pname[1:]

    def getAccessors(cls, name):
        if name[0] == '_':
            name = name[1:]
            prefix = '_'
        else:
            prefix = ''
        pname = cls._propertyToSuffix(name)
        ret = {}
        for method, (type, argcount) in cls.accessors.iteritems():
            accessor = getattr(cls, '%s%s%s' % (prefix, method, pname), None)
            ret[type] = accessor
        return ret

class PythonEgg(object):
    """PythonEgg class

    Main features:
        - auto-creation of properties
    """

    __metaclass__ = MetaEgg

    def __init__(self, *args, **kwargs):
        self._createMetaAttributes()
        super(PythonEgg, self).__init__(*args, **kwargs)

    def _createMetaAttributes(self):
        for name, value in self.__class__.__dict__.iteritems():
            if self._isMetaAttribute(name, value):
                setattr(self, name, value(self))

    def _isMetaAttribute(self, name, attr_value):
        if isinstance(attr_value, MetaAttribute):
            return True
        if  inspect.isclass(attr_value) \
        and issubclass(attr_value, AttributeClass):
            return True

class MetaAttribute(PythonEgg):
    def __init__(self, creator, *args, **kwargs):
        super(MetaAttribute, self).__init__()
        self._creator = creator
        self._args = args
        self._kwargs = kwargs

    def __call__(self, owner):
        return self._creator(owner, *self._args, **self._kwargs)

class AttributeClass(PythonEgg):
    def __init__(self, owner):
        self.owner = owner
        super(AttributeClass, self).__init__()
