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
import textwrap

from svc.egg import PythonEgg
from svc.utils import issequence

class HelpManager(PythonEgg):
    def __init__(self, manager, extractors, screenWidth=80):
        self._manager = manager
        self._extractors = extractors
        self._ex_help = [e.helpForOptions for e in extractors]
        self._screenWidth = screenWidth

    def _wrapParagraphs(self, str, width=70):
        paragraphs = []
        for line in str.splitlines(True):
            line = line.lstrip()
            if not line and paragraphs and paragraphs[-1]:
                paragraphs.append('')
            elif not paragraphs:
                paragraphs.append(line)
            else:
                paragraphs[-1] += line
        paragraphs = [textwrap.wrap(par, width) for par in paragraphs]
        paragraphs = ['\n'.join(par) for par in paragraphs]
        return '\n\n'.join(paragraphs)


    def getHelpDict(self, screenWidth=None):
        if screenWidth is None:
            screenWidth = self._screenWidth

        option_help = {}

        for ehelp in self._ex_help:
            if ehelp is None:
                continue
            for opt_name, opt_desc in ehelp.iteritems():
                if opt_name not in option_help:
                    option_help[opt_name] = []
                if not issequence(opt_desc):
                    opt_desc = [opt_desc]
                option_help[opt_name].extend(opt_desc)

        max_desc_width = 0

        manager_help = self._manager.helpForOptions

        for opt_name in option_help:
            opt_doc = manager_help.get(opt_name, '')
            opt_desc = option_help[opt_name]
            opt_desc = ', '.join(opt_desc)
            max_desc_width = max(max_desc_width, len(opt_desc))
            option_help[opt_name] = (opt_desc, opt_doc)

        padding = 2

        template = '%%-%ds' % max_desc_width + ' '*padding

        wrap_width = max(screenWidth - max_desc_width - padding, 30)

        str_help = {} 
        for opt_name, (opt_desc, opt_doc) in option_help.iteritems():
            par = []
            lines = self._wrapParagraphs(opt_doc, wrap_width).splitlines() or ['']
            for line in lines:
                par.append(template % opt_desc + line)
                opt_desc = ''
            str_help[opt_name] = '\n'.join(par).rstrip()
        return str_help

    def getHelpDictOptions(self, options, screenWidth=None):
        ret = self.getHelpDict(screenWidth)
        new = {}
        for opt_name in options:
            if opt_name in ret:
                new[opt_name] = ret[opt_name]
        return new

    def getFuncDoc(self, func, screenWidth=None):
        if screenWidth is None:
            screenWidth = self._screenWidth

        doc = getattr(func, '__doc__')
        if doc is None:
            doc = ''
        doc = doc.strip()

        return self._wrapParagraphs(doc, screenWidth)


    def printHelpDictOptions(self, options, screenWidth=None, stdout=None, newline=False):
        if stdout is None:
            stdout = sys.stdout
        help = self.getHelpDictOptions(options, screenWidth)
        help = [i[1] for i in sorted(help.items())]
        if help:
            stdout.write('\n'.join(help) + '\n')
            if newline:
                stdout.write('\n')

    def printHelpDictOptionsHdr(self, options, header, screenWidth=None, stdout=None, newline=False):
        self.printHeader(header, stdout)
        self.printHelpDictOptions(options, screenWidth, stdout, newline)

    def printFuncDoc(self, func, screenWidth=None, stdout=None, newline=False):
        if stdout is None:
            stdout = sys.stdout
        help = self.getFuncDoc(func, screenWidth)
        if help:
            stdout.write(help + '\n')
            if newline:
                stdout.write('\n')

    def printHeader(self, header, stdout=None, head_str='='):
        if stdout is None:
            stdout = sys.stdout
        stdout.write(header + ':\n')
        stdout.write(head_str * (len(header)+1) + '\n')

    def printHelpForCommand(self, command, method, screenWidth=None, stdout=None):
        if stdout is None:
            stdout = sys.stdout
        self.printHeader(command, stdout, head_str='~')

        self.printFuncDoc(method, screenWidth, stdout, newline=True)

        command_params = self._manager.paramsChildren(command)
        command_options = [self._manager.paramToOption(p) for p in command_params]
        if command_options:
            self.printHelpDictOptions(command_options, screenWidth, stdout)
        else:
            stdout.write("No options available\n")
        stdout.write('\n')

    def printUsage(self, script_file, pos_opts, main_obj=None, screenWidth=None, stdout=None):
        if stdout is None:
            stdout = sys.stdout

        pos_opts_str = []
        for o in pos_opts:
            if o == Ellipsis:
                pos_opts_str.append('...')
            elif isinstance(o, dict):
                pos_opts_str.append('...')
            else:
                pos_opts_str.append(o.title())
        pos_opts_str = ' '.join(pos_opts_str)

        self.printHeader('Usage', stdout, head_str='=')
        stdout.write('    %s [options] %s\n' % (script_file, pos_opts_str))
        stdout.write('\n')
        if main_obj is not None:
            self.printFuncDoc(main_obj, screenWidth, stdout, newline=True)
