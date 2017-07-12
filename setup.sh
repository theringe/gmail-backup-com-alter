#!/bin/bash
#python2.5 -O /usr/lib/python2.5/py_compile.py gmail-backup-gui.py
#python2.5 -O /usr/lib/python2.5/py_compile.py gmail-backup.py
#python2.5 -O /usr/lib/python2.5/py_compile.py gmb.py
mkdir dist_SH
cp gmail-backup.py gmail-backup-gui.py gmb.py dist_SH
cp gmb.gif gmb.ico dist_SH
cp gmail-backup.pot dist_SH

svn export messages dist_SH/messages
cp -r svc dist_SH
rm -rf dist_SH/svc/.svn
rm -rf dist_SH/svc/scripting/.svn
