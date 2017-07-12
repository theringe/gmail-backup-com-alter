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
import os
import re
import time
import getpass
from copy import copy
from threading import Thread
from select import select
from subprocess import Popen, PIPE

from svc.egg import PythonEgg, MetaEgg
from svc.scripting import *
from svc.utils import sym, issequence

import warnings

Generator = sym('Generator')
AllowOverwrite = sym('AllowOverwrite')
OmitStdout = sym('OmitStdout')
AsyncMethod = sym('AsyncMethod')
# TODO:
# GNUargs = sym('GNUargs')
ExecGenerator = sym('ExecGenerator')
ExecList = sym('ExecList')
ExecStr = sym('ExecStr')
ExecNoStdout = sym('ExecNoStdout')
ExecAsync = sym('ExecAsync')

class ExternalError(OSError):
    pass

class ExternalMethod(PythonEgg):
    def __init__(self, file_name, name=None, args=[], logger=None, env=None, path=None, etype=ExecGenerator, pre_func=None, post_func=None):
        super(ExternalMethod, self).__init__()
        if path is None:
            self.fileName = file_name
        else:
            self.fileName = os.path.join(path, file_name)
        if name is None:
            self.name = os.path.basename(file_name)
        else:
            self.name = name
        self.args = args
        self.logger = logger
        self.env = env
        if self.getExecuteMethod(etype) is None:
            raise ValueError("Unknown execute type: %r" % etype)
        self.etype = etype
        self.pre_func = pre_func
        self.post_func = post_func

    def _logStderr(self, line):
        if self.logger:
            self.logger(self, line)
        else:
            sys.stderr.write(line)

    def getOSEnv(self):
        return dict(os.environ)

    def getEnv(self):
        e = self.getOSEnv()
        if self._env is not None:
            e.update(self._env)
        return e

    def setEnv(self, env):
        self._env = env

    def _strEnv(self, env):
        ret = {}
        for key, value in env.iteritems():
            ret[key] = str(value)
        return ret

    def _strArgs(self, args):
        return [str(a) for a in args]
    
    def getArgs(self):
        return self._args

    def setArgs(self, args):
        self._args = args

    def execute(self, *args, **kwargs):
        """Executes program `fn` with cmdline `args` and in environment `env`

        It would raise an ExternalError if the program `fn` returned non-zero
        exit status. Environment of new process is initialized using
        `self.getEnv` method and updated with `env`.

        :Returns:
            Generator yielding lines of stdout of `fn`
        """
        stdin = kwargs.pop('stdin', None)
        stdin_file = kwargs.pop('stdin_file', None)
        stdout_file = kwargs.pop('stdout_file', None)
        env = kwargs.pop('env', {})

        if kwargs:
            raise TypeError("Bad keyword arguments: %s" % kwargs.keys())

        if stdin is not None and stdin_file is not None:
            raise TypeError("You cannot use both stdin and stdin_file argument")

        e = dict(self.getEnv())
        e.update(env)
        e = self._strEnv(e)
        args = self._strArgs(self.args + list(args))

        to_close = []

        if stdin is not None:
            stdin_func = iter(stdin)
            stdin = PIPE
        elif stdin_file is not None:
            stdin_func = None
            stdin = file(stdin_file, 'r')
            to_close.append(stdin)
        else:
            stdin_func = None
            stdin = None

        if stdout_file is not None:
            stdout = file(stdout_file, 'w')
            to_close.append(stdout)
        else:
            stdout = PIPE

        exec_list = [self.fileName] + args
        if self.pre_func is not None:
            self.pre_func(self, exec_list, env)
        try:
            process = Popen(exec_list, shell=False, env=e,
                    stdin=stdin, stdout=stdout, stderr=PIPE, bufsize=0)
        except OSError, e:
            raise ExternalError("Couldn't execute external method %r: %s" % (self.name, e))

        stdin = process.stdin
        stdout = process.stdout
        stderr = process.stderr
        if stdout_file is not None:
            poll_r = [stderr]
        else:
            poll_r = [stdout, stderr]
        if stdin_func is not None:
            poll_w = [stdin]
        else:
            poll_w = []

        while poll_r or poll_w:
            readable, writeable, errorable = select(poll_r, poll_w, [])

            if stderr in readable:
                line = stderr.readline()
                if not line:
                    stderr.close()
                    poll_r.remove(stderr)
                else:
                    self._logStderr(line)
                    continue

            if stdout in readable:
                line = stdout.readline()
                if not line:
                    stdout.close()
                    poll_r.remove(stdout)
                else:
                    yield line

            if stdin in errorable:
                poll_w.remove(stdin)
            elif stdin in writeable:
                try:
                    stdin.write(stdin_func.next())
                except StopIteration:
                    stdin.close()
                    poll_w.remove(stdin)

        retcode = process.wait()
        for f in to_close:
            f.close()
        if self.post_func is not None:
            self.post_func(self, exec_list, env)
        if retcode < 0:
            raise ExternalError("External method %s (%r) killed by signal (%d)" % (self.name, ' '.join(exec_list), -retcode))
        elif retcode > 0:
            raise ExternalError("External method %s (%r) returned with nonzero exit status (%d)" % (self.name, ' '.join(exec_list), retcode))

    def executeGenerator(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    __iter__ = executeGenerator

    def executeList(self, *args, **kwargs):
        return list(self.execute(*args, **kwargs))

    def executeStr(self, *args, **kwargs):
        return ''.join(self.execute(*args, **kwargs))

    def executeNoStdout(self, *args, **kwargs):
        for foo in self.execute(*args, **kwargs):
            pass

    def executeAsync(self, *args, **kwargs):
        t = Thread(target=self.executeNoStdout, args=args, kwargs=kwargs)
        t.setDaemon(False)
        t.start()
        return t

    def getExecuteMethod(self, etype):
        etype = str(etype)
        if not etype.startswith('Exec'):
            return None
        etype = etype[4:]
        return getattr(self, 'execute%s' % etype, None)

    def __call__(self, *args, **kwargs):
        m = self.getExecuteMethod(self.etype)
        return m(*args, **kwargs)

    def new(self, *args, **kwargs):
        if 'stdin' in kwargs:
            stdin = kwargs.pop('stdin')
        else:
            stdin = None

        if 'env' in kwargs:
            env = kwargs.pop('env')
        else:
            env = {}

        if kwargs:
            raise TypeError("Bad keyword arguments: %s" % kwargs.keys())

        e = dict(self.getEnv())
        e.update(env)
        e = self._strEnv(e)
        args = self._strArgs(self.args + list(args))

        ret = copy(self)
        ret.setArgs(args)
        return ret


    # Pipeline overloading
    def __or__(left, right):
        return Pipeline( (left, right) )

    def __ror__(right, left):
        return Pipeline( (left, right) )

    def __rshift__(self, fn):
        return Pipeline( (self,), redir_stdout=fn)

    def __rrshift__(self, fn):
        return Pipeline( (self,), redir_stdin=fn)

class Pipeline(PythonEgg):
    def __init__(self, pipeline, redir_stdin=None, redir_stdout=None):
        super(Pipeline, self).__init__()
        self.setupPipeline(pipeline, redir_stdin, redir_stdout)

    def setupPipeline(self, pipeline, redir_stdin, redir_stdout):
        ret = []

        no_stdin = False

        for i, item in enumerate(pipeline):
            first = (i==0)
            last = (i==len(pipeline)-1)

            item_callable = callable(item)

            if not item_callable:
                if first:
                    no_stdin = True
                else:
                    raise ValueError("Items in pipeline must be callable")

            if isinstance(item, Pipeline):
                if first and item.redir_stdin is not None:
                    if redir_stdin:
                        raise ValueError("Input of pipeline is redirected")
                    else:
                        redir_stdin = item.redir_stdin
                if last and item.redir_stdout is not None:
                    if redir_stdout:
                        raise ValueError("Output of pipeline is redirected")
                    else:
                        redir_stdout = item.redir_stdout
                ret.extend(item._pipeline)
            else:
                if not callable(item):
                    if first:
                        no_stdin = True
                    else:
                        raise ValueError("Items in pipeline must be callable")
                ret.append(item)

        self._pipeline = tuple(ret)
        self.no_stdin = no_stdin
        self.redir_stdin = redir_stdin
        self.redir_stdout = redir_stdout

    def getOSEnv(self):
        return dict(os.environ)

    def _strEnv(self, env):
        ret = {}
        for key, value in env.iteritems():
            ret[key] = str(value)
        return ret

    def execute(self, stdin=None, env={}):
        e = self.getOSEnv()
        e.update(env)
        e = self._strEnv(e)

        pipeline = self._pipeline

        if self.no_stdin and stdin is not None:
            raise ValueError("Pipeline doesn't have a stdin")
        
        if self.redir_stdin and stdin is not None:
            raise ValueError("Pipeline have a redirected stdin")
        
        generator = stdin
        for i, item in enumerate(pipeline):
            first = (i==0)
            last = (i==len(pipeline)-1)

            if isinstance(item, ExternalMethod):
                if not last:
                    method = item.executeGenerator
                else:
                    method = item
                kwargs = {}
                if self.redir_stdin is not None and first:
                    kwargs['stdin_file'] = self.redir_stdin
                else:
                    kwargs['stdin'] = generator
                if self.redir_stdout is not None and last:
                    kwargs['stdout_file'] = self.redir_stdout
                generator = method(env=e, **kwargs)
            elif callable(item):
                generator = item(generator)
            else:
                generator = item
        return generator

    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    def __iter__(self):
        return self.execute()

    # Pipeline overloading
    def __or__(left, right):
        return Pipeline( (left, right) )

    def __ror__(right, left):
        return Pipeline( (left, right) )

    def __rshift__(self, fn):
        return Pipeline( (self,), redir_stdout=fn)

    def __rrshift__(self, fn):
        return Pipeline( (self,), redir_stdin=fn)

class MetaExternalMethods(MetaEgg):
    def __init__(cls, name, bases, dict):
        super(MetaExternalMethods, cls).__init__(name, bases, dict)
        if cls.externalMethods:
            cls.__bases__ = cls.__bases__ + (cls.createClassExternals(), )

    def createClassExternals(cls):
        class rClass(object):
            pass

        rClass.__name__ = '%sExternals' % cls.__name__
        rClass.__module__ = cls.__module__

        meth_dict = cls.unifyExternalMethods(cls.externalMethods)
        done_dict = {}

        for dir in cls.externalMethodDirs:
            for meth_name in os.listdir(dir):
                meth_path = os.path.join(dir, meth_name)
                if meth_name in meth_dict:
                    # TODO: Check for inconsitencies in method specifiers
                    if Generator in meth_dict[meth_name]:
                        warnings.warn("Don't use Generator, use ExecGenerator instead", DeprecationWarning, 3)
                        meth = cls.createMethod(meth_name, meth_path, ExecGenerator)
                    elif OmitStdout in meth_dict[meth_name]:
                        warnings.warn("Don't use OmitStdout, use ExecNoStdout instead", DeprecationWarning, 3)
                        meth = cls.createMethod(meth_name, meth_path, ExecNoStdout)
                    elif AsyncMethod in meth_dict[meth_name]:
                        warnings.warn("Don't use AsyncMethod, use ExecAsync instead", DeprecationWarning, 3)
                        meth = cls.createMethod(meth_name, meth_path, ExecAsync)
                    elif ExecGenerator in meth_dict[meth_name]:
                        meth = cls.createMethod(meth_name, meth_path, ExecGenerator)
                    elif ExecNoStdout in meth_dict[meth_name]:
                        meth = cls.createMethod(meth_name, meth_path, ExecNoStdout)
                    elif ExecAsync in meth_dict[meth_name]:
                        meth = cls.createMethod(meth_name, meth_path, ExecAsync)
                    else:
                        meth = cls.createMethod(meth_name, meth_path, ExecList)

                    if ExScript.command in meth_dict[meth_name]:
                        meth = ExScript.command(meth)
                        child_meth = getattr(cls, meth_name, None)
                        if child_meth is not None and not ExScript.isCommand(child_meth):
                            raise TypeError("External method %r defined as ExScript.command, but method in derived class %r is not decorated" % \
                                                (meth_name, cls.__name__))

                    if meth_name in done_dict and AllowOverwrite not in meth_dict[meth_name]:
                        raise TypeError("External method %r is defined in two different places: %r and %r" % \
                                                (meth_name, done_dict[meth_name], dir))
                    setattr(rClass, meth_name, meth)

                    done_dict[meth_name] = dir

        rest = set(meth_dict) - set(done_dict)
        if rest:
            raise ValueError('External method %r not found' % rest.pop())

        return rClass

    def unifyExternalMethods(cls, em):
        ret = {}
        for meth_name, specifiers in em.iteritems():
            if issequence(specifiers):
                ret[meth_name] = set(specifiers)
            else:
                ret[meth_name] = set([specifiers])
        return ret

    def createMethod(cls, name, path, etype):
        def rMethod(self, *args, **kwargs):
            meth = ExternalMethod(path, name=name, etype=etype,
                    logger=self._logExternalStderr, env=self._externalEnv,
                    pre_func=self._logPreExec, post_func=self._logPostExec)
            return meth(*args, **kwargs)

        cls.adoptMethod(rMethod, name)
        return rMethod

    def adoptMethod(cls, meth, name):
        meth.__name__ = name
        meth.__module__ = cls.__module__


class ExternalMethods(PythonEgg):
    __metaclass__ = MetaExternalMethods
    externalMethodDirs = []
    externalMethods = {}

    def _logPreExec(self, method, cmdline, env):
        pass

    def _logPostExec(self, method, cmdline, env):
        pass

    def _logExternalStderr(self, method, line):
        sys.stdout.write(line)

    def _getExternalEnv(self):
        return os.environ

class ExternalScript(ExScript, ExternalMethods):
    externalMethodDirs = []
    externalMethods = {}
    settingsFiles = []

    def __init__(self, *args, **kwargs):
        super(ExternalScript, self).__init__(*args, **kwargs)
        self._settings = dict(os.environ)

    def getSettings(self):
        return self._settings

    def sourceEnv(self, fn):
        SKIP = ['PWD', 'SHLVL', '_']
        env = Popen(['/bin/bash', '-c', 'source %s; env' % fn], env=self.settings, stdout=PIPE).communicate()[0]
        for line in env.splitlines():
            try:
                name, val = line.split('=', 1)
            except ValueError:
                continue
            if val.startswith('()'):
                continue
            if name in SKIP: continue
            self.settings[name] = val

    def storeEnv(self, fn, info={}):
        AU = 'Author'
        DT = 'Date'
        FN = 'Filename'
        info = dict(info)

        info[AU] = getpass.getuser()
        info[DT] = time.strftime('%Y-%m-%d-%H:%M:%S')
        info[FN] = os.path.basename(fn)
        key_order = [AU, DT, FN]

        fw = file(fn, 'w')
        try:
            fw.write("#!/bin/bash\n\n")
            while info:
                if key_order:
                    key = key_order.pop(0)
                else:
                    key = sorted(info)[0]
                value = info.pop(key)
                fw.write("# %20s:  %s\n" % (key, value))
            fw.write('\n')

            for key, value in sorted(self.settings.items()):
                value = str(value)
                if key not in os.environ or value != os.environ[key]:
                    if re.search(r'\s', value):
                        fw.write('export %s="%s"\n' % (key, value))
                    else:
                        fw.write('export %s=%s\n' % (key, value))

            fw.write("\n\n###########################\n#  Operating environment  #\n###########################\n\n")
            for key, value in sorted(os.environ.items()):
                if re.search(r'\s', value):
                    fw.write('# %s="%s"\n' % (key, value))
                else:
                    fw.write('# %s=%s\n' % (key, value))
        finally:
            fw.close()

    def _getExternalEnv(self):
        return self.settings

    def _logPreExec(self, method, cmdline, env):
        self.logger.info('Running external method %s.%s (%r)', self.__class__.__name__, method.name, ' '.join(cmdline))

    def _logExternalStderr(self, method, line):
        for l in line.splitlines():
            self.logger.error('%s.%s: %s', self.__class__.__name__, method.name, l)

    def getManagerArgs(self):
        m_args = super(ExternalScript, self).getManagerArgs()
        m_args['specification'].update({
            '__premain__.settings': (Multiple, String),
        })
        m_args['docs'].update({
            'settings': "Additional shell files with settings",
        })
        return m_args

    def premain(self, settings=[], **kwargs):
        ret = super(ExternalScript, self).premain(**kwargs)
        settings = self.settingsFiles + settings
        for fn in settings:
            self.sourceEnv(fn)
        return ret
