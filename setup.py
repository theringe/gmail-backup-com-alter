#!/usr/bin/env python2.5
# -*-  coding: utf-8 -*-
#
#   Gmail Backup setup script
#   
#   Copyright © 2008, 2009, 2010 Jan Svec <honza.svec@gmail.com> and Filip Jurcicek <filip.jurcicek@gmail.com>
#   
#   This file is part of Gmail Backup.
#
#   Gmail Backup is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free
#   Software Foundation, either version 3 of the License, or (at your option)
#   any later version.
#
#   Gmail Backup is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#   FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#   more details.
#
#   You should have received a copy of the GNU General Public License along
#   with Gmail Backup.  If not, see <http://www.gnu.org/licenses/
#
#   See LICENSE file for license details

from distutils.core import setup
import py2exe
import sys
from glob import glob

setup(
    # The first three parameters are not required, if at least a
    # 'version' is given, then a versioninfo resource is built from
    # them and added to the executables.

    # targets to build
    #windows = ['lmedit.py'],
    console = ['gmail-backup.py'], 
    windows = [{'script': 'gmail-backup-gui.py', 'icon_resources': [(1, 'gmb.ico')]}],
    options = {'py2exe':
                    {'optimize': 2,
                     "dll_excludes": ["msvcp90.dll"],
                    }
              },
    data_files = [
            ('.', ['gmb.gif', 'gmb.ico']),
        ]
)
