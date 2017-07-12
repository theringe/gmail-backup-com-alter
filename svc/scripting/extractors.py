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

"""Extraktory sloužící třídě `Script`

Všechny extraktory musí implementovat rozhraní `Extractor`. Je-li jim jako
zdroj pomocí `Extractor.setSource` předána hodnota ``None``, musí být použit
implicitní zdroj. Extraktory vytváří metoda `Script.createExtractors`, proto po
případném přidání extraktoru nezapomeňte tuto metodu modifikovat.

.. image:: ../uml6.png
"""

__docformat__ = 'restructuredtext cs'

import sys
from os.path import expanduser, isfile
import os

from svc.utils import issequence, seqIntoDict
from svc.scripting import Extractor, Multiple, EnvVar, JoinSources
from svc.scripting.conversions import Flag
from getopt import gnu_getopt as getopt

class CmdlineExtractor(Extractor):
    def __init__(self, short_opts={}, pos_opts=[]):
        self.setSource(None)
        self.setPosOpts(pos_opts)
        self.setShortOpts(short_opts)
    
    def getPosOpts(self):
        return self._posOpts
    
    def setPosOpts(self, pos_opts):
        seqIntoDict([], pos_opts)
        self._posOpts = pos_opts
    
    def getShortOpts(self):
        return self._shortOpts
    
    def setShortOpts(self, short_opts):
        for key, value in short_opts.iteritems():
            if len(key) != 1:
                raise ValueError("Bad key in short_opts dictionary: %r" % key)
            if value in self.posOpts:
                raise ValueError("Positional option cannot have short form: %r" % key)
        self._shortOpts = short_opts

    def getSource(self):
        return self._source
    
    def setSource(self, source):
        self._source = source
    
    def getSourceName(self):
        return 'argv'
    
    def extract(self, state):
        source = self.getSource()
        if source is None:
            source = sys.argv[1:]

        short = self._getoptShort()
        long = self._getoptLong()

        options, positional = getopt(source, short, long)

        self._extractGetoptOpt(state, options)
        self._extractGetoptPos(state, positional)

    def _extractGetoptOpt(self, state, options):
        with_arg = self._optionsWithArg()
        source_name = self.getSourceName()
        for option, value in options:
            if option.startswith('--'):
                opt_name = option[2:]
            else:
                opt_name = self._shortOpts[option[1:]]
            # Map back from the command-line form into underscored form
            opt_name = opt_name.replace('-', '_')
            if opt_name in with_arg:
                state.append( (opt_name, value, source_name, option) )
            else:
                state.append( (opt_name, 'true', source_name, option) )

    def _extractGetoptPos(self, state, positional):
        source_name = self.getSourceName()
        pos_opts = self.posOpts
        d = seqIntoDict(positional, pos_opts)
        state.addObjects(d, source_name, positional)
    
    def setManager(self, manager):
        self._manager = manager
    
    def _optionsWithArg(self):
        m = self._manager
        return set(m.paramToOption(p) for p in m.params()
                   if m.conversion(p)[0] != Flag)
    
    def _getoptShort(self):
        with_arg = self._optionsWithArg()
        ret = []
        for short, long in self._shortOpts.iteritems():
            if long in self.posOpts:
                # Positional options cannot have short-option form
                continue
            ret.append(short)
            if long in with_arg:
                ret.append(':')
        return ''.join(ret)
    
    def _getoptLong(self):
        with_arg = self._optionsWithArg()
        ret = []
        for o in self._manager.options():
            if o in self.posOpts:
                # Positional options don't have long-option form
                continue
            if o in with_arg:
                o += '='
            # Map into command-line form (tj. '_' maps to '-')
            o = o.replace('_', '-')
            ret.append(o)
        return ret

    def getHelpCmdline(self):
        def mapEllipsis(item):
            if item is not Ellipsis:
                return str(item).title()
            else:
                return '...'
        opts = self._posOpts
        return ' '.join(mapEllipsis(i) for i in self._posOpts)

    def getHelpForOptions(self):
        ret = {}
        reverse_short = dict((item, key) for (key, item) in self.shortOpts.iteritems())
        for o in self._manager.options():
            help = []
            if o in reverse_short:
                help.append('-%s, ' % reverse_short[o])
            else:
                help.append('    ')
            if o in self._posOpts:
                help.append(o.title())
            else:
                help.append('--%s' % o.replace('_', '-'))
            ret[o] = ''.join(help)
        return ret


class PyFileExtractor(Extractor):
    def __init__(self, globals=None, app_source=None):
        self.setSource(None)
        self.setAppSource(app_source)
        if globals is None:
            globals = {}
        self.setGlobals(globals)
        self._processedFiles = set()

    def getSource(self):
        return self._source
    
    def setSource(self, source):
        self._source = source
    
    def getAppSource(self):
        return self._appSource

    def setAppSource(self, source):
        self._appSource = source

    def getGlobals(self):
        return self._globals

    def setGlobals(self, globals):
        self._globals = globals
    
    def getSourceName(self):
        return 'pyfiles'

    def _prepareSource(self, source):
        """Předpřipraví zdroj `source`

        Je-li `source` None, vrátí [], není-li `source` posloupnost, vrátí
        ``[source]``. Ve výsledku expanduje znak tilda ``~`` na domovský
        adresář aktuálního uživatele. Z výsledku odstraní již zpracované
        soubory podle `processedFiles`.

        :See:
            processedFiles
        """
        if source is None:
            source = []
        elif not issequence(source):
            source = [source]
        source = [f for f in (expanduser(f) for f in source) if isfile(f)]
        source = [f for f in source if f not in self.processedFiles]
        return source

    def _extractFromFile(self, pyfile):
        globals = self.getGlobals()
        locals = {}
        self._processedFiles.add(pyfile)
        execfile(pyfile, globals, locals)
        ret = []
        for opt_name, value in locals.iteritems():
            if isinstance(value, (list, tuple)):
                # If option has assigned the list- or tuple-value, insert
                # distinct items from this sequence
                for item in value:
                    ret.append( (opt_name, item, pyfile, '') )
            else:
                ret.append( (opt_name, value, pyfile, '') )
        return ret
    
    def extract(self, state):
        self._processedFiles.clear()

        while True:
            source = self._prepareSource(self.getSource()) \
                     + self._prepareSource(self.getAppSource())
            if not source:
                break
            state.extend(self._extractFromFile(source[0]))

    def getProcessedFiles(self):
        return self._processedFiles
    
    def setManager(self, manager):
        self._manager = manager


class EnvironExtractor(Extractor):
    def __init__(self, env_prefix=None, split_char=None):
        self.setSource(None)
        self.setEnvPrefix(env_prefix)
        if split_char is None:
            if os.name == 'nt':
                self.setSplitChar(';')
            else:
                self.setSplitChar(':')
        else:
            self.setSplitChar(split_char)
    
    def getSource(self):
        return self._source
    
    def setSource(self, source):
        self._source = source
    
    def getEnvPrefix(self):
        return self._envPrefix
    
    def setEnvPrefix(self, prefix):
        self._envPrefix = prefix
    
    def getSplitChar(self):
        return self._splitChar

    def setSplitChar(self, s_char):
        self._splitChar = s_char
    
    def getSourceName(self):
        return 'env'

    def setManager(self, manager):
        self._manager = manager
    
    def extract(self, state):
        source = self._source
        if source is None:
            source = os.environ
        env_vars = self._manager.optionsWithSpecifier(EnvVar)
        multiple_vars  = self._manager.optionsWithSpecifier(Multiple) 
        multiple_vars |= self._manager.optionsWithSpecifier(JoinSources) # Union of sets
        prefix = self.getEnvPrefix()
        if not issequence(prefix):
            prefix = [prefix]
        if not prefix:
            prefix = [None]
        prefix = [p or '' for p in prefix]
        split_char = self.getSplitChar()

        for p in prefix:
            for var in env_vars:
                whole_var = (p+var).upper()
                if whole_var in source:
                    value = source[whole_var]
                    if var in multiple_vars:
                        for item in value.split(split_char):
                            state.append( (var, item, 'env:%s'%p, whole_var) )
                    else:
                        state.append( (var, value, 'env:%s'%p, whole_var) )


class CmdPosOptsExtractor(Extractor):
    def __init__(self, exscript):
        super(CmdPosOptsExtractor, self).__init__()
        self._exscript = exscript

    def getSource(self):
        return None
    
    def setSource(self, source):
        pass
    
    def getSourceName(self):
        return 'cmdPosOpts'

    def getPosOpts(self, state):
        cmdPosOption = '__premain__._command_pos_opts'
        enabled = state.enabled
        try:
            state.disableAll()
            state.enable([cmdPosOption])
            try:
                objects = state.getObjects()
                return objects['__premain__']['_command_pos_opts']
            except KeyError:
                return []
        finally:
            state.disableExcept(enabled)
    
    def extract(self, state):
        try:
            command = self._exscript.getCommandValue().pop()
        except ValueError:
            # Command wasn't specified
            return
        if command in self._exscript.cmdPosOpts:
            format = self._exscript.cmdPosOpts[command]
            pos_opts = self.getPosOpts(state)
            d = seqIntoDict(pos_opts, format)
            self._exscript.state.addObjects(d, 'cmdPosOpts')
    
    def setManager(self, manager):
        pass

    def getHelpForOptions(self):
        return {}

    def getHelpForExtractor(self):
        return ''
