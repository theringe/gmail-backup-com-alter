#!/usr/bin/env python
# -*-  coding: utf-8 -*-
#
#   Gmail Backup CLI
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

from svc.scripting import *
from gmb import ConsoleNotifier, _convertTime, GMailBackup, GMB_REVISION, GMB_DATE, imap_decode, imap_encode
import sys

GMB_CMD_REVISION = u'-Revision: 12345 -'
GMB_CMD_DATE = u'-Date: 2017-07-12 -'

GMB_CMD_REVISION = GMB_CMD_REVISION[11:-2]
GMB_CMD_DATE = GMB_CMD_DATE[7:-2].split()[0]
 
MAX_REVISION = str(max(int(GMB_CMD_REVISION), int(GMB_REVISION)))
MAX_DATE = max(GMB_CMD_DATE, GMB_DATE)


try:
    from hashlib import md5
except ImportError:
    from md5 import md5

class GMailBackupScript(ExScript):
    USAGE = \
'''Description
===========

Program for backup and restore of your GMail mailbox. You will need to activate
the IMAP access to your mailbox, to do so, please open your GMail settings and
under POP/IMAP tab activate this option.

The messages are stored in the local directory in files which names follow the
format YYYYMMDD-hhmmss-nn.eml where YYYY is the year, MM the month number, DD
is the day number, hh are hours, mm are minutes and ss are seconds when the
e-mail was SENT. For the case there is more emails with the same timestamp
there is the number nn which starts with value 1. Label assignment is stored in
the file labels.txt which is the plain text file and it pairs the emails stored
in the file described above with the assigned labels.

Examples:
=========

To perform full backup of your GMail account into directory dir, use:

gmail-backup.exe backup dir user@gmail.com password

To specify time interval, you can add additional date specification in the
format YYYYMMDD. The second date can be ommited in which case the backup is
from the first date to now:

gmail-backup.exe backup dir user@gmail.com password 20070621 20080101

You can do multiple backups into the same directory. The labels.txt is updated
according the new e-mails not in the previous backup.

To restore your backup use the restore command. To restore your GMail account
from the previous backup in the directory dir, use for example:

gmail-backup.exe restore dir user@gmail.com password

You can also use the extra feature of GMail backup. It allows the user to
completely clear his mailbox (for example if the user wants to end using the
GMail). All messages are permanently deleted (of course the email can be stored
somewhere deep in the Google company). To do so, execute the command:

gmail-backup.exe clear user@gmail.com password

The program will ask you to repeat the username, so you have the chance to
cancel your mistake.

Backups with timestamp:
=======================

Since 0.10 release GMail Backup has great feature - it stores the date of the
last backup for future usage. The date is stored in the backup directory in the
file "stamp". If there is no starting date (20070621 in the example above), the
stored stamp is used. The "stamp" is updated to be the latest date from the
stored emails during the last backup.

To use this feature, simple use the --stamp command line flag:

gmail-backup.exe backup dir user@gmail.com password --stamp

Note:
=====

Under Linux, you have to use the "gmail-backup.sh" script distributed in
another ZIP file instead of the Windows binary "gmail-backup.exe".


Error reporting:
================

If you want to report some errors in this software, please use our user support 
mailing list:

gmail-backup-com-users@googlegroups.com

To speed up the solution of your problem, please run the program with --debug
command line option and include full traceback of the error. Include also the
version of GMail Backup you have used.
Thanks.
'''

    options = {
        'command': ExScript.CommandParam,
        'backup.dirname': (Required, String),
        'backup.username': (Required, String),
        'backup.password': (Required, String),
        'backup.before': (String),
        'backup.since': (String),
        'backup.stamp': Flag,
        'restore.dirname': OptionAlias,
        'restore.username': OptionAlias,
        'restore.password': OptionAlias,
        'restore.before': OptionAlias,
        'restore.since': OptionAlias,
        'clear.username': OptionAlias,
        'clear.password': OptionAlias,
        'list.username': OptionAlias,
        'list.password': OptionAlias,
    }

    posOpts = ['command', {'backup': ['dirname', 'username', 'password', 'since', 'before'],
                           'restore': ['dirname', 'username', 'password', 'since', 'before'],
                           'clear': ['username', 'password'],
                           'list': ['username', 'password'],
                           'version': [],
                          }]

    optionsDoc = {
        'command': 'Action to perform - backup or restore.',
        'dirname': '''Directory which will contain (or contains - for restore)
                    the backup of your mailbox.''',
        'username': '''Your GMail account, eg. foo.bar@gmail.com''',
        'password': '''Your GMail password''',
        'since': '''Only e-mails since this date are backed up, date in format YYYYMMDD''',
        'before': '''Only e-mails before this date are backed up, date in format YYYYMMDD''',
    }

    debugMain = False

    def printHelp(self):
        print self.USAGE

    @ExScript.command
    def backup(self, dirname, username, password, since=None, before=None, stamp=False):
        '''Performs backup of your GMail mailbox'''
        self.notifier = ConsoleNotifier()

        where = ['ALL']
        if since:
            since = _convertTime(since)
            where.append('SINCE')
            where.append(since)
        if before:
            before = _convertTime(before)
            where.append('BEFORE')
            where.append(before)

        b = GMailBackup(username, password, self.notifier)
        b.backup(dirname, where, stamp=stamp)

    @ExScript.command
    def restore(self, dirname, username, password, since=None, before=None):
        '''Performs restore of your previously backed up GMail mailbox'''
        self.notifier = ConsoleNotifier()
        b = GMailBackup(username, password, self.notifier)
        b.restore(dirname, since, before)

    @ExScript.command
    def clear(self, username, password):
        '''Clear this GMail mailbox (remove all messages and labels). To avoid
        unintentionally deletion of your messages, you have to reenter your
        mailbox name.'''
        mailbox = raw_input("Do you want to delete all messages from your mailbox (%s)?\nPlease, repeat the name of your mailbox: " % username)
        if mailbox != username:
            print "Mailbox names doesn't match"
            return
        self.notifier = ConsoleNotifier()
        b = GMailBackup(username, password, self.notifier)
        b.clear()

    @ExScript.command
    def list(self, username, password):
        '''List the names and number of messages of GMail IMAP mailboxes.
        
        Usefull for debugging and for gathering information about new supported
        language. If your GMail language is not supported, don't hesitate and
        write us to user support group:
            
            gmail-backup-com-users@googlegroups.com

        '''
        self.notifier = ConsoleNotifier()
        b = GMailBackup(username, password, self.notifier)
        for item, n_messages in b.list():
            print item, imap_decode(item).encode('utf-8'), n_messages, ' '*8

    @ExScript.command
    def version(self):
        self.notifier = ConsoleNotifier()
        b = GMailBackup(None, None, self.notifier)
        b.reportNewVersion()

    def _mainError(self, value):
        if isinstance(value, OptionError):
            return super(GMailBackupScript, self)._mainError(value)
        elif not hasattr(self, 'notifier'):
            return super(GMailBackupScript, self)._mainError(value)
        else:
            type, error, tb = sys.exc_info()
            self.notifier.nException(type, error, tb)
        sys.exit(1)

    def _mainErrorFull(self, type, value, tb):
        if hasattr(self, 'notifier'):
            self.notifier.nExceptionFull(type, value, tb)
        else:
            traceback.print_exception(type, value, tb)
        sys.exit(1)



if __name__ == '__main__':
    s = GMailBackupScript()
    s.run()
