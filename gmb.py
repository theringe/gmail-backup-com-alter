#!/usr/bin/env python2.5
# -*-  coding: utf-8 -*-
#
#   Gmail Backup library
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

import os
import sys
import imaplib
import socket
import zipfile
import email
import email.Utils
import email.Header
import email.Iterators
import email.Header
import email.Generator
import email.Errors
import sys
if sys.version_info[:2] >= (2, 5):
    import email.utils
    import email.header
    import email.iterators
    import email.header
    import email.generator
    import email.errors

import time
import datetime
import re
import codecs
import socket
import traceback
import shutil
import urllib
import zipfile
import string
import unicodedata
import gettext

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

GMB_REVISION = u'-Revision: 12345 -'  # Changed manually as I do not have access to the SVN repository. I preferred "20a", but that makes the program fail. And I don't want to mess with the official revision range.
GMB_DATE = u'-Date: 2017-07-12 -'  # Changed manually as I do not have access to the SVN repository.

GMB_REVISION = GMB_REVISION[11:-2]
GMB_DATE = GMB_DATE[7:-2].split()[0]

SPEED_AVERAGE_TIME = 21 # speed average over the last x seconds
SOCKET_TIMEOUT = 60 # timeout for socket operations

MAX_LABEL_RETRIES = 5

VERSION_URL = 'http://code.google.com/p/gmail-backup-com/source/list'

SLEEP_FOR = 20 # After network error sleep for X seconds
MAX_TRY = 5 # Maximum number of reconnects

MESSAGES_DIR = os.path.join(os.path.dirname(sys.argv[0]), 'messages')
gettext.install('gmail-backup', MESSAGES_DIR, unicode=1)

def _onlyAscii(string):
    if isinstance(string, unicode):
        return string.encode('ascii', 'replace')
    else:
        return string.decode('ascii', 'replace').encode('ascii', 'replace')

def _parseMsgId(msg):
    msg_id = msg['Message-Id']
    if not msg_id:
        from_ = msg['From']
        subj = msg['Subject']
        hash = md5()
        hash.update(msg.as_string())
        msg_id = '%s.%s.%s' % (from_, subj, hash.hexdigest())
    else:
        msg_id = msg_id.lstrip('<').rstrip('>')
    msg_id = _onlyAscii(msg_id)
    return msg_id

def _getMailInternalId(mail):
    msg = email.message_from_string(mail)
    return _parseMsgId(msg)

def _getMailDate(mail):
    msg = email.message_from_string(mail)
    return _parseMsgDate(msg)

def _getMailIMAPDate(mail):
    msg = email.message_from_string(mail)
    d = imaplib.Time2Internaldate(_parseMsgDate(msg))
    return d

def _convertTime(t):
    t = time.mktime(time.strptime(t, '%Y%m%d'))
    return imaplib.Time2Internaldate(t)

def _convertTimeToNum(t):
    t = time.mktime(time.strptime(t, '%Y%m%d'))
    return t

def _unicodeHeader(hdr):
    try:
        ret = []
        for item, enc in email.Header.decode_header(hdr):
            try:
                if enc is not None:
                    ret.append(item.decode(enc))
                else:
                    ret.append(item.decode('ascii', 'replace'))
            except UnicodeDecodeError, LookupError:
                ret.append(item.decode('ascii', 'replace'))
        return ''.join(ret)
    except:
        return _('<unparseable header>')

def _getMsgInitials(msg):
    '''Returns from_address and subject for parsed `email` message
    '''
    from_address = _unicodeHeader(msg['From'])
    match = re.match(r"^.*<(.*@.*\..*)>.*$", from_address)
    if match:
        from_address = match.group(1)
    subject = _unicodeHeader(msg['Subject'])
    return from_address, subject

def _getMailInitials(mail):
    msg = email.message_from_string(mail)
    return _getMsgInitials(msg)
    

def _trimDate(d):
    def trim(mi, va, ma):
        if va < mi:
            return mi
        elif va > ma:
            return ma
        else:
            return va
    (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst) = d
    tm_year = trim(1970, tm_year, 9999)
    tm_mon = trim(1, tm_mon, 12)
    tm_mday = trim(1, tm_mday, 31)
    tm_hour = trim(0, tm_hour, 23)
    tm_min = trim(0, tm_min, 59)
    tm_sec = trim(0, tm_sec, 59)
    tm_yday = trim(1, tm_yday, 366)
    if tm_isdst not in [-1, 0, 1]:
        tm_isdst = -1
    d = (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
    try:
        # We will try to construct the time
        time.mktime(d)
    except OverflowError:
        # If overflow error occurs, we will fallback to 0
        d = time.localtime(0)
    return d

def _parseMsgDate(msg):
    d = email.Utils.parsedate(msg['Date'])
    if d is None:
        d = time.localtime(0)
    d = _trimDate(d)
    return d

def _revertDict(d):
    return dict((v, k) for (k, v) in d.iteritems())

def _shiftDates(min_date, max_date):
    min_date = _trimDate(min_date)
    max_date = _trimDate(max_date)
    shift_ts = 24*60*60 # 1 hour
    try:
        min_t = time.localtime(time.mktime(min_date)-shift_ts)
    except ValueError:
        min_t = time.localtime(time.mktime(min_date))
    try:
        max_t = time.localtime(time.mktime(max_date)+shift_ts)
    except ValueError:
        max_t = time.localtime(time.mktime(max_date))
    min_t = _trimDate(min_t)
    max_t = _trimDate(max_t)
    return min_t, max_t

def imap_decode(s):
    def sub(m):
        ss = m.groups(1)[0]
        if not ss:
            return '&'
        else:
            ss = ('+'+ss+'-').replace(',', '/')
            return ss.decode('utf-7')
    return re.sub('&(.*?)-', sub, s)

def imap_encode(s):
    def sub(m):
        ss = m.groups(1)[0]
        if ss == '&':
            return '&-'
        else:
            return ss.encode('utf-7').replace('+', '&').replace('/', ',')
    return re.sub('([^\x20-\x25\x27-\x7e]+|&)', sub, s).encode('ascii', 'replace')

def imap_unescape(s):
    ret = re.sub(r'\\([\\"])', r'\1', s)
    return ret

def imap_escape(s):
    ret = re.sub(r'([\\"])', r'\\\1', s)
    return ret

def _removeDiacritics(string):
    '''Removes any diacritics from `string`
    '''
    if not isinstance(string, unicode):
        string = unicode(string)
    string = unicodedata.normalize('NFKD', string)

    output = ''
    for c in string:
        if not unicodedata.combining(c):
            output += c
    return output

class GBNotifier(object):
    def nVersion(self):
        pass

    def nSpeed(self, amount, d):
        pass

    def nBackup(self, end, mailbox, directory):
        pass

    def nRestore(self, end, mailbox, directory):
        pass

    def nClear(self, end, mailbox):
        pass

    def nEmailBackup(self, from_address, subject, num, total):
        pass

    def nEmailBackupSkip(self, num, total, skipped, total_to_skip):
        pass

    def nEmailRestore(self, from_address, subject, num, total):
        pass

    def nEmailRestoreSkip(self, from_address, subject, num, total):
        pass

    def nLabelsBackup(self, end):
        pass

    def nLabelsRestore(self, num, total):
        pass

    def nError(self, msg):
        pass
    
    def nLog(self, msg):
        pass

    def nException(self, type, error, tb):
        pass

    def nExceptionFull(self, type, error, tb):
        pass

    def nExceptionMsg(self, msg, type, error, tb):
        pass

    def getSpeed(self):
        pass

    def getTotal(self):
        pass

    def getPercentage(self):
        pass

    def updateSpeed(self):
        pass

class ConsoleNotifier(GBNotifier):
    FATAL_ERRORS = [socket.error, imaplib.IMAP4.abort, imaplib.IMAP4.error, KeyboardInterrupt]

    def __init__(self, *args, **kwargs):
        super(ConsoleNotifier, self).__init__(*args, **kwargs)
        self._resetCounters()

    def _resetCounters(self):
        self._speed = []
        self._total = 0
        self._percentage = None

    def uprint(self, msg):
        try:
            print msg
        except UnicodeEncodeError:
            print msg.encode('ascii', 'replace')
        sys.stdout.flush()

    def uprint2(self, msg):
        if not sys.stdout.isatty():
            return
        try:
            print '\r%s    \r' % (msg, ),
        except UnicodeEncodeError:
            print '\r%s    \r' % (msg.encode('ascii', 'replace'), ),
        sys.stdout.flush()

    def nVersion(self):
        self.nLog(_("GMail Backup revision %s (%s)") % (GMB_REVISION, GMB_DATE))

    def nSpeed(self, amount, d):
        self._total += amount
        self._speed.insert(0, (amount, d))
        d_sum = 0
        for idx, (a, d) in enumerate(self._speed):
            d_sum += d
            if d_sum > SPEED_AVERAGE_TIME:
                break
        del self._speed[idx+1:]
        self.updateSpeed()

    def getSpeed(self):
        a_sum = 0
        d_sum = 0
        for a, d in self._speed:
            d_sum += d
            a_sum += a
        if d_sum == 0:
            return 0
        else:
            return (a_sum/d_sum)/1024.

    def getTotal(self):
        return self._total/1024./1024.

    def getPercentage(self):
        return self._percentage

    def updateSpeed(self):
        self.uprint2(_("%1.fKB/s (total: %.2fMB)") % (self.getSpeed(), self.getTotal()))

    def nBackup(self, end, mailbox, directory):
        if not end:
            self._resetCounters()
        if not end:
            self.uprint(_("Starting backup of account %s into %s") % (mailbox, directory))
        else:
            self.uprint(_("Ending backup of account %s") % (mailbox, ))

    def nRestore(self, end, mailbox, directory):
        if not end:
            self._resetCounters()
        if not end:
            self.uprint(_("Restoring the content of account %s from %s") % (mailbox, directory))
        else:
            self.uprint(_("End of restoring of account %s") % (mailbox, ))

    def nClear(self, end, mailbox):
        if not end:
            self.uprint(_("Clearing the content of account %s") % (mailbox, ))
        else:
            self.uprint(_("End of clearing of account %s") % (mailbox, ))

    def nEmailBackup(self, from_address, subject, num, total):
        self._percentage = float(num)/total*100
        self.uprint(_("Stored %4.1f%% (%d of %d): %s - %s") % (self._percentage, num, total, from_address, subject))

    def nEmailBackupSkip(self, num, total, skipped, total_to_skip):
        self._percentage = float(num)/total*100
        self.uprint(_("Skip   %4.1f%% (%d of %d): message already stored") % (self._percentage, num, total))

    def nEmailRestore(self, from_address, subject, num, total):
        self._percentage = float(num)/total*100
        self.uprint(_("Restored %4.1f%%: %s - %s") % (self._percentage, from_address, subject))

    def nEmailRestoreSkip(self, from_address, subject, num, total):
        self._percentage = float(num)/total*100
        self.uprint(_("Skipdate %4.1f%%: %s - %s") % (self._percentage, from_address, subject))

    def nLabelsBackup(self, end):
        if not end:
            self.uprint(_("Starting backup of labels"))
        else:
            self.uprint(_("Backup of labels ended"))

    def nLabelsRestore(self, num, total):
        self.uprint(_("Restoring labels, %.1f%%") % (float(num)/total*100, ))

    def nError(self, msg):
        self.uprint(_('Error: %s') % msg)

    def nLog(self, msg):
        self.uprint(unicode(msg))

    def nException(self, type, error, tb):
        if isinstance(error, socket.error):
            #num, message = error
            self.nError(_('%s\nThere are network problems, please, try it later') % (error, ))
        elif isinstance(error, imaplib.IMAP4.abort):
            self.nError(_("IMAP aborted the transfer"))
        elif isinstance(error, imaplib.IMAP4.error):
            self.nError(_("IMAP: %s") % error.message)
        elif isinstance(error, KeyboardInterrupt):
            self.nLog(_("Program interrupted by user"))
        else:
            self.nExceptionFull(type, error, tb)

    def nExceptionFull(self, type, error, tb):
        t = ''.join(traceback.format_exception(type, error, tb))
        self.nError(_("Error occured, full traceback is bellow (gmb.py revision %s)\n%s") % (GMB_REVISION, t))

    def nExceptionMsg(self, msg, type, error, tb):
        t = ''.join(traceback.format_exception(type, error, tb))
        self.nError(_("%s\nIgnoring this error message.\nIf you want, please report the following traceback to gmail-backup-com-users@googlegroups.com \nThanks! (gmb.py revision %s):\n%s") % (msg, GMB_REVISION, t))

    def handleError(self, msg):
        e_type, e_value, e_tb = sys.exc_info()
        for e in self.FATAL_ERRORS:
            if isinstance(e_value, e):
                raise
        self.nExceptionMsg(msg, e_type, e_value, e_tb)

class MyIMAP4_SSL(imaplib.IMAP4_SSL):
    '''Hack for bad implementation of sock._recv() under windows'''
    def open(self, *args, **kwargs):
        imaplib.IMAP4_SSL.open(self, *args, **kwargs)
        self.sock.settimeout(SOCKET_TIMEOUT)
        self._t1 = time.time()

    def setNotifier(self, notifier):
        self.notifier = notifier

    def _nSpeed(self, t1, t2, amount):
        if hasattr(self, 'notifier'):
            d = t2 - t1
            self.notifier.nSpeed(amount, d)

    def read(self, size):
        step = 1024 * 32
        ret = []
        while size > 0:
            part = imaplib.IMAP4_SSL.read(self, min(size, step))
            t2 = time.time()
            ret.append(part)
            self._nSpeed(self._t1, t2, len(part))
            self._t1 = t2
            size -= step
        return ''.join(ret)

    def send(self, data):
        step = 1024 * 32
        idx = 0
        while idx < len(data):
            part = data[idx:idx+step]
            imaplib.IMAP4_SSL.send(self, part)
            t2 = time.time()
            self._nSpeed(self._t1, t2, len(part))
            self._t1 = t2
            idx += step

class GMailConnection(object):
    ALL_MAILS = None
    TRASH = None
    OK = 'OK'

    MAILBOX_NAMES = {
        'en_us': ('[Gmail]/All Mail', '[Gmail]/Trash'),
        'en_uk': ('[Gmail]/All Mail', '[Gmail]/Bin'),
        'cs': ('[Gmail]/V&AWE-echny zpr&AOE-vy', '[Gmail]/Ko&AWE-'),
        'es': ('[Gmail]/Todos', '[Gmail]/Papelera'),
        'de': ('[Gmail]/Alle Nachrichten', '[Gmail]/Papierkorb'),
        'fr': ('[Gmail]/Tous les messages', '[Gmail]/Corbeille'),
        'ar': ('[Gmail]/&BkMGRA- &BicGRAYoBjEGSgYv-', '[Gmail]/&BkUGRwZABkUGRAYnBio-'),
        'it': ('[Gmail]/Tutti i messaggi', '[Gmail]/Cestino'),
        'pl': ('[Gmail]/Wszystkie', '[Gmail]/Kosz'),
        'sk': ('[Gmail]/V&AWE-etky spr&AOE-vy', '[Gmail]/K&APQBYQ-'),
        'bahasa_indonesia': ('[Gmail]/Semua Email', '[Gmail]/Tong Sampah'),
        'bahasa_melayu': ('[Gmail]/Semua Mel', '[Gmail]/Sampah'),
        'catala': ('[Gmail]/Tots els missatges', '[Gmail]/Paperera'),
        'dansk': ('[Gmail]/Alle e-mails', '[Gmail]/Papirkurv'),
        'eesti_keel': ('[Gmail]/K&APU-ik kirjad', '[Gmail]/Pr&APw-gikast'),
        'filipino': ('[Gmail]/Lahat ng Mail', '[Gmail]/Basurahan'),
        'hrvatski': ('[Gmail]/Sva po&AWE-ta', '[Gmail]/Otpad'),
        'islenska': ('[Gmail]/Allur p&APM-stur', '[Gmail]/Rusl'),
        'latviesu': ('[Gmail]/Visas v&ARM-stules', '[Gmail]/Miskaste'),
        'lietuviu': ('[Gmail]/Visi lai&AWE-kai', '[Gmail]/&AWA-iuk&AWE-liad&ARcBfgEX-'),
        'magyar': ('[Gmail]/&ANY-sszes lev&AOk-l', '[Gmail]/Kuka'),
        'norsk': ('[Gmail]/All e-post', '[Gmail]/Papirkurv'),
        'nederlands': ('[Gmail]/Alle berichten', '[Gmail]/Prullenbak'),
        'portugues_brazil': ('[Gmail]/Todos os e-mails', '[Gmail]/Lixeira'),
        'portugues_portugal': ('[Gmail]/Todo o correio', '[Gmail]/Lixo'),
        'romana': ('[Gmail]/Toate mesajele', '[Gmail]/Co&AV8- de gunoi'),
        'slovenscina': ('[Gmail]/Vsa po&AWE-ta', '[Gmail]/Smetnjak'),
        'suomi': ('[Gmail]/Kaikki viestit', '[Gmail]/Roskakori'),
        'svenska': ('[Gmail]/Alla mail', '[Gmail]/Papperskorgen'),
        'tieng_viet': ('[Gmail]/T&AOIDAQ-t ca&Awk- Th&AbA-', '[Gmail]/Thu&AwA-ng Ra&AwE-c'),
        'turkce': ('[Gmail]/T&APw-m Postalar', '[Gmail]/&AMcA9g-p Kutusu'),
        'ellnvika': ('[Gmail]/&A4wDuwOx- &A8QDsQ- &A7wDtwO9A80DvAOxA8QDsQ-', '[Gmail]/&A5oDrAO0A78Dwg- &A7EDwAO,A8EDwQO5A7wDvAOsA8QDyQO9-'),
        'azbuka1': ('[Gmail]/&BBIEQQRP- &BD8EPgRHBEIEMA-', '[Gmail]/&BBoEPgRABDcEOAQ9BDA-'),
        'azbuka2': ('[Gmail]/&BCEEMgQw- &BD8EPgRIBEIEMA-', '[Gmail]/&BB4EQgQ,BDAENA-'),
        'azbuka3': ('[Gmail]/&BCMEQQRP- &BD8EPgRIBEIEMA-', '[Gmail]/&BBoEPgRIBDgEOg-'),
        'azbuka4': ('[Gmail]/&BCYETwQ7BDAEQgQw- &BD8EPgRJBDA-', '[Gmail]/&BBoEPgRIBEcENQ-'),
        'hebrew': ('[Gmail]/&BdsF3A- &BdQF0wXVBdAF6A-', '[Gmail]/&BdAF6QXkBdQ-'),
        'arabic': ('[Gmail]/&BkMGRA- &BicGRAYoBjEGSgYv-', '[Gmail]/&BkUGRwZABkUGRAYnBio-'),
        'caj1': ('[Gmail]/&CTgJLQlA- &CS4JRwky-', '[Gmail]/&CR8JTQkwCUgJNg- &CRUJMAlHCQI-'),
        'caj2': ('[Gmail]/&DggOFA4rDiEOMg4iDhcOMQ5JDgcOKw4hDhQ-', '[Gmail]/&DhYOMQ4HDgIOIg4w-'),
        'caj3': ('[Gmail]/&UWiQ6JD1TvY-', '[Gmail]/&V4NXPmh2-'),
        'caj4': ('[Gmail]/&YkBnCZCuTvY-', '[Gmail]/&XfJSIJZkkK5O9g-'),
        'caj5': ('[Gmail]/&MFkweTBmMG4w4TD8MOs-', '[Gmail]/&MLQw33ux-'),
        'caj6': ('[Gmail]/&yATMtLz0rQDVaA-', '[Gmail]/&1zTJwNG1-'),
        # The same with Google Mail instead of Gmail
        'en_us_GM': ('[Google Mail]/All Mail', '[Google Mail]/Trash'),
        'en_uk_GM': ('[Google Mail]/All Mail', '[Google Mail]/Bin'),
        'cs_GM': ('[Google Mail]/V&AWE-echny zpr&AOE-vy', '[Google Mail]/Ko&AWE-'),
        'es_GM': ('[Google Mail]/Todos', '[Google Mail]/Papelera'),
        'de_GM': ('[Google Mail]/Alle Nachrichten', '[Google Mail]/Papierkorb'),
        'fr_GM': ('[Google Mail]/Tous les messages', '[Google Mail]/Corbeille'),
        'ar_GM': ('[Google Mail]/&BkMGRA- &BicGRAYoBjEGSgYv-', '[Google Mail]/&BkUGRwZABkUGRAYnBio-'),
        'it_GM': ('[Google Mail]/Tutti i messaggi', '[Google Mail]/Cestino'),
        'pl_GM': ('[Google Mail]/Wszystkie', '[Google Mail]/Kosz'),
        'sk_GM': ('[Google Mail]/V&AWE-etky spr&AOE-vy', '[Google Mail]/K&APQBYQ-'),
        'bahasa_indonesia_GM': ('[Google Mail]/Semua Email', '[Google Mail]/Tong Sampah'),
        'bahasa_melayu_GM': ('[Google Mail]/Semua Mel', '[Google Mail]/Sampah'),
        'catala_GM': ('[Google Mail]/Tots els missatges', '[Google Mail]/Paperera'),
        'dansk_GM': ('[Google Mail]/Alle e-mails', '[Google Mail]/Papirkurv'),
        'eesti_keel_GM': ('[Google Mail]/K&APU-ik kirjad', '[Google Mail]/Pr&APw-gikast'),
        'filipino_GM': ('[Google Mail]/Lahat ng Mail', '[Google Mail]/Basurahan'),
        'hrvatski_GM': ('[Google Mail]/Sva po&AWE-ta', '[Google Mail]/Otpad'),
        'islenska_GM': ('[Google Mail]/Allur p&APM-stur', '[Google Mail]/Rusl'),
        'latviesu_GM': ('[Google Mail]/Visas v&ARM-stules', '[Google Mail]/Miskaste'),
        'lietuviu_GM': ('[Google Mail]/Visi lai&AWE-kai', '[Google Mail]/&AWA-iuk&AWE-liad&ARcBfgEX-'),
        'magyar_GM': ('[Google Mail]/&ANY-sszes lev&AOk-l', '[Google Mail]/Kuka'),
        'norsk_GM': ('[Google Mail]/All e-post', '[Google Mail]/Papirkurv'),
        'nederlands_GM': ('[Google Mail]/Alle berichten', '[Google Mail]/Prullenbak'),
        'portugues_brazil_GM': ('[Google Mail]/Todos os e-mails', '[Google Mail]/Lixeira'),
        'portugues_portugal_GM': ('[Google Mail]/Todo o correio', '[Google Mail]/Lixo'),
        'romana_GM': ('[Google Mail]/Toate mesajele', '[Google Mail]/Co&AV8- de gunoi'),
        'slovenscina_GM': ('[Google Mail]/Vsa po&AWE-ta', '[Google Mail]/Smetnjak'),
        'suomi_GM': ('[Google Mail]/Kaikki viestit', '[Google Mail]/Roskakori'),
        'svenska_GM': ('[Google Mail]/Alla mail', '[Google Mail]/Papperskorgen'),
        'tieng_viet_GM': ('[Google Mail]/T&AOIDAQ-t ca&Awk- Th&AbA-', '[Google Mail]/Thu&AwA-ng Ra&AwE-c'),
        'turkce_GM': ('[Google Mail]/T&APw-m Postalar', '[Google Mail]/&AMcA9g-p Kutusu'),
        'ellnvika_GM': ('[Google Mail]/&A4wDuwOx- &A8QDsQ- &A7wDtwO9A80DvAOxA8QDsQ-', '[Google Mail]/&A5oDrAO0A78Dwg- &A7EDwAO,A8EDwQO5A7wDvAOsA8QDyQO9-'),
        'azbuka1_GM': ('[Google Mail]/&BBIEQQRP- &BD8EPgRHBEIEMA-', '[Google Mail]/&BBoEPgRABDcEOAQ9BDA-'),
        'azbuka2_GM': ('[Google Mail]/&BCEEMgQw- &BD8EPgRIBEIEMA-', '[Google Mail]/&BB4EQgQ,BDAENA-'),
        'azbuka3_GM': ('[Google Mail]/&BCMEQQRP- &BD8EPgRIBEIEMA-', '[Google Mail]/&BBoEPgRIBDgEOg-'),
        'azbuka4_GM': ('[Google Mail]/&BCYETwQ7BDAEQgQw- &BD8EPgRJBDA-', '[Google Mail]/&BBoEPgRIBEcENQ-'),
        'hebrew_GM': ('[Google Mail]/&BdsF3A- &BdQF0wXVBdAF6A-', '[Google Mail]/&BdAF6QXkBdQ-'),
        'arabic_GM': ('[Google Mail]/&BkMGRA- &BicGRAYoBjEGSgYv-', '[Google Mail]/&BkUGRwZABkUGRAYnBio-'),
        'caj1_GM': ('[Google Mail]/&CTgJLQlA- &CS4JRwky-', '[Google Mail]/&CR8JTQkwCUgJNg- &CRUJMAlHCQI-'),
        'caj2_GM': ('[Google Mail]/&DggOFA4rDiEOMg4iDhcOMQ5JDgcOKw4hDhQ-', '[Google Mail]/&DhYOMQ4HDgIOIg4w-'),
        'caj3_GM': ('[Google Mail]/&UWiQ6JD1TvY-', '[Google Mail]/&V4NXPmh2-'),
        'caj4_GM': ('[Google Mail]/&YkBnCZCuTvY-', '[Google Mail]/&XfJSIJZkkK5O9g-'),
        'caj5_GM': ('[Google Mail]/&MFkweTBmMG4w4TD8MOs-', '[Google Mail]/&MLQw33ux-'),
        'caj6_GM': ('[Google Mail]/&yATMtLz0rQDVaA-', '[Google Mail]/&1zTJwNG1-'),
    }

    def __init__(self, username, password, notifier, lang=None):
        self.username = username
        self.password = password
        self.notifier = notifier
        self.lang = None
        if lang is not None:
            self.setLanguage(lang)
        self._lastMailbox = None
        self._lastSearch = None
        self._lastFetched = None
        self._lastFetchedMsg = None
        self._wasLogged = False

    def recoverableError(self, e):
        if isinstance(e, (socket.error, imaplib.IMAP4_SSL.abort, socket.timeout)):
            return True
        elif isinstance(e, imaplib.IMAP4_SSL.error):
            str_e = str(e)
            if self._wasLogged and 'Invalid credentials' in str_e:
                return True
        return False

    def guessLanguage(self):
        present = set()

        status, ret = self.con.list()
        for i in ret:
            match = re.match(r'^\(.*\)\s".*"\s"(\[.*\].*)"\s*$', i)
            if not match:
                continue
            box = match.group(1)
            present.add(box)

        for key, (all_mail, trash) in self.MAILBOX_NAMES.iteritems():
            if all_mail in present and trash in present:
                return key
        for key, (all_mail, trash) in self.MAILBOX_NAMES.iteritems():
            if all_mail in present:
                self.notifier.nLog("Guessing language with internal code '%s', in case of problems contact us at honza.svec@gmail.com" % key)
                return key
        self.notifier.nError(\
'''Your Gmail account doesn't export some IMAP needed to Gmail Backup work.
Possible causes are:
- You are using the Gmail Labs.
  Please go to the Settings/Label page and enable the IMAP access into
  All Mails and Trash folders.
- You are using unsupported language of Gmail. Please run the following
  command:

  gmail-backup.exe list <your_address@gmail.com> <your_password>

  and send the output of this command to our user support group:

  gmail-backup-com-users@googlegroups.com

  Thank you''')
        raise ValueError("Cannot access IMAP folders")

    def setLanguage(self, lang):
        self.lang = lang
        self.ALL_MAILS = self.MAILBOX_NAMES[lang][0]
        self.TRASH = self.MAILBOX_NAMES[lang][1]
    
    def connect(self, noguess=False):
        self.con = MyIMAP4_SSL('imap.gmail.com', 993)
        self.con.setNotifier(self.notifier)
        self.con.login(self.username, self.password)
        self._wasLogged = True
        if self.lang is None and not noguess:
            lang = self.guessLanguage()
            self.setLanguage(lang)

    def close(self):
        self.con.shutdown()
        del self.con

    def select(self, mailbox):
        self._lastMailbox = mailbox
        self._call(self.con.select, mailbox)

    def reconnect(self):
        TRY = 1
        sleep = SLEEP_FOR
        while TRY <= MAX_TRY:
            self.notifier.nLog(_("Trying to reconnect (%d)") % TRY)
            try:
                self.connect()
                if self._lastMailbox:
                    self.select(self._lastMailbox)
                if self._lastSearch:
                    self.search(self._lastSearch)
                self.notifier.nLog(_("Reconnected!"))
                return True
            except:
                e = sys.exc_info()[1]
                if self.recoverableError(e):
                    self.notifier.nLog(_("Not connected, sleeping for %d seconds") % SLEEP_FOR)
                    time.sleep(sleep)
                    sleep *= 2
                    TRY += 1
                else:
                    raise e
        self.notifier.nLog(_("Unable to reconnect"))
        return False

    def fetchMessageId(self, num):
        typ, data = self._call(self.con.fetch, num, '(BODY.PEEK[HEADER.FIELDS (Message-ID)])')
        if data is None or data[0] is None:
            match = None
        else:
            match = re.match(r'^.*:\s*<(.*)>$', data[0][1].strip())
        if match:
            # The message has Message-ID stored in it
            imsg_id = match.group(1)
            imsg_id = _onlyAscii(imsg_id)
            return imsg_id
        else:
            # We compute our synthetic Message-ID from the whole message
            mail = self.fetchMessage(num)
            msg = email.message_from_string(mail)
            imsg_id = _parseMsgId(msg)
            return imsg_id

    def fetchMessage(self, num):
        if self._lastFetched == num:
            return self._lastFetchedMsg
        else:
            typ, data = self._call(self.con.fetch, num, '(BODY.PEEK[])')
            mail = data[0][1]
            self._lastFetched = num
            self._lastFetchedMsg = mail
            return mail
    
    def search(self, where):
        self._lastSearch = where
        typ, numbers = self._call(self.con.search, None, *where)
        numbers = numbers[0].split()
        return numbers

    def lsub(self):
        status, ret = self._call(self.con.lsub)
        ret = [imap_unescape(i) for i in ret]
        return ret

    def list(self):
        status, ret = self._call(self.con.list)
        ret = [imap_unescape(i) for i in ret]
        return ret

    def create(self, label):
        self._call(self.con.create, label)

    def copy(self, message_set, label):
        self._call(self.con.copy, message_set, label)

    def append(self, mailbox, flags, msg_date, msg):
        self._call(self.con.append, mailbox, flags, msg_date, msg)

    def store(self, nums, state, flags):
        self._call(self.con.store, nums, state, flags)

    def expunge(self):
        self._call(self.con.expunge)

    def delete(self, mailbox):
        self._call(self.con.delete, mailbox)

    def _call(self, method, *args, **kwargs):
        # Dirty hack:
        method_name = method.im_func.__name__
        while True:
            try:
                method = getattr(self.con, method_name)
                ret = method(*args, **kwargs)
                return ret
            except:
                e = sys.exc_info()[1]
                if self.recoverableError(e):
                    self.notifier.nLog(_("Network error occured, disconnected"))
                    if not self.reconnect():
                        raise e
                else:
                    raise e

class EmailStorage(object):
    @classmethod
    def createStorage(cls, fn, notifier):
        ext = os.path.splitext(fn.split('#')[0])[1]
        if ext.lower() == '.zip':
            return ZipStorage(fn, notifier)
        else:
            return DirectoryStorage(fn, notifier)

    def idsOfMessages(self):
        '''Returns the set of stored msg_ids'''

    def iterBackups(self, since_time=None, before_time=None, logging=True):
        '''Iterates over backups specified by parameters and yields pairs (storageid, message)'''

    def store(self, msg):
        '''Stores message `msg`'''

    def getLabelAssignment(self):
        '''Returns label assignment'''

    def updateLabelAssignment(self, assignment):
        '''Updates label assignment with `assignment`'''

    def lastStamp(self):
        '''Return the stamp of the last backup, the output is in the format of _convertTime()'''

    def updateStamp(self, last_time):
        '''Updates the stamp of the last backup to last_time'''

    def _templateDict(self, msg):
        '''Creates dictionary used in the template expansion
        '''
        d = _parseMsgDate(msg)
        ret = {}
        ret['YEAR'] = time.strftime('%Y', d)
        ret['MONTH'] = time.strftime('%m', d)
        ret['DAY'] = time.strftime('%d', d)
        ret['HOUR'] = time.strftime('%H', d)
        ret['MINUTE'] = time.strftime('%M', d)
        ret['SECOND'] = time.strftime('%S', d)
        ret['FROM'], ret['SUBJ'] = _getMsgInitials(msg)
        ret['FROM'] = ret['FROM'].lower()
        
        # Replace "/" and "\" (directory separators) with "_" in all values in the dictionary ret.
        # We can't do this in _cleanFilename() as the file name being cleaned there can include valid directory separators.
        # This fixes Issue 17: https://code.google.com/p/gmail-backup-com/issues/detail?id=17.
        ret = dict((k, v.replace('/', '_').replace('\\', '_')) for (k, v) in ret.iteritems())
        
        return ret


class DirectoryStorage(EmailStorage):
    def __init__(self, fn, notifier):
        self.setFnAndFragment(fn)
        self.notifier = notifier
        self._makeMaildir()
        self._readDownloadedIds()
        self._readLabelAssignment()

    def setFnAndFragment(self, fn):
        '''Sets the filename and the pattern for naming the files in the
        storage
        '''
        items = fn.split("#", 1)
        if len(items) == 1:
            self.fn = items[0]
            self.fragment = '${YEAR}/${MONTH}/${YEAR}${MONTH}${DAY}-${HOUR}${MINUTE}${SECOND}-${FROM}-${SUBJ}'
        else:
            self.fn = items[0]
            self.fragment = items[1]
        self.fn = os.path.expanduser(self.fn)
        self.fragment = string.Template(self.fragment)

    def iterBackups(self, since_time=None, before_time=None, logging=True):
        def walkBackups(top):
            '''Walks trough the dn and returns path originating in dn and ending with '.eml'
            '''
            for dn, sub_dns, fns in os.walk(top):
                rel_dn = dn[len(top):].lstrip(os.path.sep)
                for fn in fns:
                    if os.path.splitext(fn)[1].lower() != '.eml':
                        continue
                    yield os.path.join(rel_dn, fn)

        listing = sorted(walkBackups(self.fn))
        for idx, msg_fn in enumerate(listing):
            try:
                full_msg_fn = os.path.join(self.fn, msg_fn)
                fr = file(full_msg_fn, 'rb')
                try:
                    msg = fr.read()
                finally:
                    fr.close()

                msg_date2 = _getMailDate(msg)
                msg_date2_num = time.mktime(msg_date2)
                if (since_time is None or since_time < msg_date2_num) \
                and (before_time is None or msg_date2_num < before_time):
                    yield msg_fn, msg
                    if logging:
                        from_address, subject = _getMailInitials(msg)
                        self.notifier.nEmailRestore(from_address, subject, idx+1, len(listing))
                else:
                    if logging:
                        from_address, subject = _getMailInitials(msg)
                        self.notifier.nEmailRestoreSkip(from_address, subject, idx+1, len(listing))
            except:
                if isinstance(sys.exc_info()[1], GeneratorExit):
                    break
                self.notifier.handleError(_("Error occured while reading e-mail from disc"))

    def _makeMaildir(self):
        dirs = [self.fn, os.path.join(self.fn, 'cur'), os.path.join(self.fn, 'new'), os.path.join(self.fn, 'tmp')]
        try:
            for i in dirs:
                os.makedirs(i)
        except OSError:
            pass

    def idsFilename(self):
        return os.path.join(self.fn, 'ids.txt')

    def labelFilename(self):
        return os.path.join(self.fn, 'labels.txt')

    def stampFile(self):
        return os.path.join(self.fn, 'stamp')

    def _readDownloadedIds(self):
        cache = self.idsFilename()
        self.message_iid2fn = {}
        if not os.path.isfile(cache):
            for msg_fn, msg in self.iterBackups(logging=False):
                try:
                    msg_iid = _getMailInternalId(msg)
                    self.message_iid2fn[msg_iid] = msg_fn
                except:
                    self.notifier.handleError(_("Error while reading MessageID from stored message"))
        else:
            fr = file(cache, 'r')
            for line in fr:
                try:
                    items = line.strip().split(None, 1)
                    try:
                        msg_fn = items[0]
                        msg_iid = items[1]
                        self.message_iid2fn[msg_iid] = msg_fn
                    except IndexError:
                        pass
                except:
                    self.notifier.handleError(_("Bad line in file with cached MessageIDs"))
            fr.close()
        self.message_fn2iid = _revertDict(self.message_iid2fn)

    def _writeDownloadedIds(self):
        fn = self.idsFilename()
        if os.path.exists(fn):
            os.remove(fn)
        fw = file(fn, 'w')
        for msg_iid, msg_fn in sorted(self.message_iid2fn.items(), key=lambda item: item[1]):
            try:
                line = '%s\t%s' % (msg_fn, msg_iid)
                print >> fw, line
            except:
                self.notifier.nError(_("Errorneous message in file: %s, please report it to <honza.svec@gmail.com>") % msg_fn)
        fw.close()

    def idsOfMessages(self):
        return set(self.message_iid2fn)

    def getLabelAssignment(self):
        return self.message_iid2labels.copy()

    def updateLabelAssignment(self, assignment):
        self.message_iid2labels.update(assignment)
        self._writeLabelAssignment()

    def _cleanFilename(self, fn):
        '''Cleans the filename - removes diacritics and other filesystem special characters
        '''
        fn = _removeDiacritics(fn)
        fn = fn.encode('utf-8', 'replace')
        if os.name == 'posix':
            good_chars = set('!"#\'()+-0123456789:;<=>@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]_abcdefghijklmnopqrstuvwxyz{}/\\')
        elif os.name == 'nt':
            good_chars = set("!#'()+-0123456789;=@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]_abcdefghijklmnopqrstuvwxyz{}/\\")
        else:
            good_chars = set("+-0123456789=@ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz/\\")
        ret = ''
        for c in fn:
            if c not in good_chars:
                c = '_'
            ret += c
        ret = re.sub('_+', '_', ret)
        return ret

    def getMailFilename(self, mail):
        msg = email.message_from_string(mail)
        values = self._templateDict(msg)
        fn = self.fragment.safe_substitute(values)
        fn = self._cleanFilename(fn)
        fn = fn[:100]  # Limit length of path.
        return fn

    def store(self, msg):
        msg_fn = self.getMailFilename(msg)
        msg_dn = os.path.dirname(msg_fn)
        full_dn = os.path.join(self.fn, msg_dn)
        if not os.path.isdir(full_dn):
            os.makedirs(full_dn)
        msg_iid = _getMailInternalId(msg)
        idx = 1
        while True:
            msg_fn_num = '%s-%01d.eml'%(msg_fn, idx)
            idx += 1
            full_fn_num = os.path.join(self.fn, msg_fn_num)
            if not os.path.exists(full_fn_num):
                break
        fw = file(full_fn_num, 'wb')
        try:
            fw.write(msg)
        finally:
            fw.close()
        # Only store msg_fn_num and msg_iid if the writing to the file above succeeded.
        self.message_iid2fn[msg_iid] = msg_fn_num
        self.message_fn2iid[msg_fn_num] = msg_iid

    def storeComplete(self):
        self._writeDownloadedIds()

    def _backupLabelAssignment(self):
        assign_fn = self.labelFilename()
        assign_fn_old = self.labelFilename()+'.bak'
        if os.path.exists(assign_fn):
            if os.path.exists(assign_fn_old):
                os.remove(assign_fn_old)
            shutil.copy(assign_fn, assign_fn_old)

    def _escapeLabels(self, labels):
        utf8_labels = [imap_decode(s) for s in labels]
        return ' '.join(s.replace('\t', '\\\t').replace(' ', '\\ ') for s in utf8_labels)

    def _unescapeLabels(self, string):
        lst = string.split()
        ret = []
        for i in lst:
            if ret and ret[-1][-1] == '\\':
                ret[-1] = ret[-1][:-1]+' '+i
            else:
                ret.append(i)
        ret = [imap_encode(s) for s in ret]
        return ret

    def _readLabelAssignment(self):
        fn = self.labelFilename()
        self.message_iid2labels = {}
        if os.path.isfile(fn):
            fr = codecs.open(fn, 'r', 'utf-8')
            for line in fr:
                items = line.split(None, 1)
                msg_fn = items[0]
                msg_iid = self.message_fn2iid.get(msg_fn, None)
                if msg_iid is not None:
                    self.message_iid2labels[msg_iid] = self._unescapeLabels(items[1])
            fr.close()

    def _writeLabelAssignment(self):
        self._backupLabelAssignment()
        fn = self.labelFilename()
        if os.path.exists(fn):
            os.remove(fn)
        fw = codecs.open(fn, 'w', 'utf-8')
        for msg_iid, labels in sorted(self.message_iid2labels.items()):
            msg_fn = self.message_iid2fn.get(msg_iid)
            if msg_fn is None:
                # We are unable do determine the filename for msg_iid
                continue
            print >> fw, '%s\t%s' % (msg_fn, self._escapeLabels(labels))
        fw.close()

    def lastStamp(self):
        stampFile = self.stampFile()
        try:
            fr = file(stampFile, 'r')
            for line in fr:
                last_time = line.strip()
                break
            fr.close()
        except IOError:
            last_time = None

        if last_time is not None:
            last_time = time.strptime(last_time, '%Y%m%d')
        return last_time

    def updateStamp(self, last_time):
        if last_time is None:
            return

        last_time = time.strftime('%Y%m%d', last_time)

        stampFile = self.stampFile()
        if os.path.exists(stampFile):
            os.remove(stampFile)
        fw = file(stampFile, 'w')
        print >> fw, last_time
        fw.close()

class ZipStorage(DirectoryStorage):
    def __init__(self, fn, notifier):
        self.setFnAndFragment(fn)
        self.notifier = notifier
        self._openZipFile()
        self._readDownloadedIds()
        self._readLabelAssignment()

    def setFnAndFragment(self, fn):
        super(ZipStorage, self).setFnAndFragment(fn)
        self.zip_fn = self.fn
        self.fn = os.path.dirname(self.fn)

    def _openZipFile(self):
        try:
            os.makedirs(self.fn)
        except OSError:
            pass

    def idsFilename(self):
        fn = os.path.splitext(self.zip_fn)[0] + '.ids.txt'
        return fn

    def labelFilename(self):
        fn = os.path.splitext(self.zip_fn)[0] + '.labels.txt'
        return fn

    def stampFile(self):
        fn = os.path.splitext(self.zip_fn)[0] + '.stamp.txt'
        return fn


    def iterBackups(self, since_time=None, before_time=None, logging=True):
        if os.path.exists(self.zip_fn):
            zip = zipfile.ZipFile(self.zip_fn, 'r')
            listing = [i.filename for i in zip.infolist()]
            # skip labels.txt and labels.txt.bak files
            for idx, msg_fn in enumerate(listing):
                try:
                    msg = zip.read(msg_fn)

                    msg_date2 = _getMailDate(msg)
                    msg_date2_num = time.mktime(msg_date2)
                    if (since_time is None or since_time < msg_date2_num) \
                    and (before_time is None or msg_date2_num < before_time):
                        yield msg_fn, msg
                        if logging:
                            from_address, subject = _getMailInitials(msg)
                            self.notifier.nEmailRestore(from_address, subject, idx+1, len(listing))
                    else:
                        if logging:
                            from_address, subject = _getMailInitials(msg)
                            self.notifier.nEmailRestoreSkip(from_address, subject, idx+1, len(listing))
                except:
                    if isinstance(sys.exc_info()[1], GeneratorExit):
                        break
                    self.notifier.handleError(_("Error occured while reading e-mail from disc"))

    def store(self, msg):
        if not os.path.exists(self.zip_fn):
            zip = zipfile.ZipFile(self.zip_fn, 'w', zipfile.ZIP_DEFLATED)
        else:
            zip = zipfile.ZipFile(self.zip_fn, 'a', zipfile.ZIP_DEFLATED)

        try:
            listing = zip.namelist()

            msg_fn = self.getMailFilename(msg)
            msg_iid = _getMailInternalId(msg)
            idx = 1
            while True:
                msg_fn_num = '%s-%01d.eml'%(msg_fn, idx)
                idx += 1
                if not msg_fn_num in listing:
                    break
            zip.writestr(msg_fn_num, msg)
        finally:
            zip.close()
        # Only store msg_fn_num and msg_iid if the writing to the zip file above succeeded.
        self.message_iid2fn[msg_iid] = msg_fn_num
        self.message_fn2iid[msg_fn_num] = msg_iid


class GMailBackup(object):
    def __init__(self, username, password, notifier, lang=None):
        self.notifier = notifier
        self.username = username
        self.password = password
        self.connection = GMailConnection(username, password, notifier, lang)

    def iterMails(self, where, skip=[]):
        self.connection.select(self.connection.ALL_MAILS)

        numbers = self.connection.search(where)

        skipped = 0
        for idx, num in enumerate(numbers):
            try:
                imsg_id = self.connection.fetchMessageId(num)
                if imsg_id in skip:
                    skipped += 1
                    self.notifier.nEmailBackupSkip(idx+1, len(numbers), skipped, len(skip))
                    continue

                msg = self.connection.fetchMessage(num)
                yield msg
                from_address, subject = _getMailInitials(msg)
                self.notifier.nEmailBackup(from_address, subject, idx+1, len(numbers))
            except:
                if isinstance(sys.exc_info()[1], GeneratorExit):
                    break
                self.notifier.handleError(_("Error occured while downloading e-mail"))

        self.connection.close()

    def getLabels(self):
        ret = self.connection.list()
        labels = []
        for i in ret:
            match = re.match(r'^(\(.*\))\s".*?"\s"(.*)"\s*$', i)
            flags = match.group(1)
            if '\\HasNoChildren' not in flags:
                continue
            label = match.group(2)
            if not re.match(r'^\[.*\].*$', label) and label != 'INBOX':
                labels.append(label)
        labels.append('INBOX')
        return labels

    def msgsWithLabel(self, label, where=['ALL']):
        self.connection.select(label)
        retries = 0
        while True:
            try:
                numbers = self.connection.search(where)
                break
            except imaplib.IMAP4.error:
                retries += 1
                if retries > MAX_LABEL_RETRIES:
                    self.notifier.nError(_("Cannot backup the assignment of label: %s") % label)
                    raise StopIteration
                else:
                    self.connection.select(label)

        for num in numbers:
            yield self.connection.fetchMessageId(num)

    def labelAssignment(self, where=['ALL']):
        assignment = {}

        self.connection.connect()
        for i in self.getLabels():
            try:
                for msg in self.msgsWithLabel(i, where):
                    if msg not in assignment:
                        assignment[msg] = set()
                    assignment[msg].add(i)
            except:
                self.notifier.handleError(_("Error while doing backup of label %r") % i)
        return assignment

    def backup(self, fn, where=['ALL'], stamp=False):
        storage = EmailStorage.createStorage(fn, self.notifier)

        last_time = storage.lastStamp()
        if last_time is not None:
            since = _convertTime(time.strftime('%Y%m%d', last_time))
            if stamp:
                try:
                    idx = where.index('SINCE')
                    where[idx+1] = since
                except ValueError:
                    where.append('SINCE')
                    where.append(since)

        self.notifier.nVersion()
        self.notifier.nBackup(False, self.username, fn)

        self.connection.connect()

        downloaded = storage.idsOfMessages()

        try:
            w = []
            for item in where:
                if item[:1] == '"':
                    item = item[:12]+'"'
                    item = item[1:-1]
                    item = item.strip()
                w.append(item)
            where = w
            """ DEBUG """
            """ self.notifier.nError(_("where: %s") % where) """
            for msg in self.iterMails(where, downloaded):
                try:
                    storage.store(msg)
                    msg_date = _getMailDate(msg)
                    if msg_date > last_time or last_time is None:
                        last_time = msg_date
                except:
                    self.notifier.handleError(_("Error while saving e-mail"))
        finally:
            storage.storeComplete()

        self.notifier.nLabelsBackup(False)

        assignment = self.labelAssignment(where)
        storage.updateLabelAssignment(assignment)

        self.notifier.nLabelsBackup(True)

        storage.updateStamp(last_time)

        self.notifier.nBackup(True, self.username, fn)
    
    def restoreLabels(self, assignment, min_date, max_date):
        self.connection.select(self.connection.ALL_MAILS)

        where = []
        where.append('SINCE')
        where.append(min_date)
        where.append('BEFORE')
        where.append(max_date)

        numbers = self.connection.search(where)

        message_by_labels = {}
        labels = set()

        for idx, num in enumerate(numbers):
            try:
                imsg_id = self.connection.fetchMessageId(num)
                if imsg_id in assignment:
                    for label in assignment[imsg_id]:
                        if label not in message_by_labels:
                            message_by_labels[label] = []
                        message_by_labels[label].append(num)
                        labels.add(label)
                self.notifier.nLabelsRestore(idx+1, len(numbers))
            except:
                self.notifier.handleError(_("Error while getting MessageID"))

        for label in labels:
            try:
                message_set = message_by_labels[label]
                message_set = ','.join(message_set)
                self.connection.create(label)
                self.connection.copy(message_set, label)
            except:
                self.notifier.handleError(_("Error while restoring label %r") % label)

    def restore(self, fn, since_time=None, before_time=None):
        if since_time:
            since_time = _convertTimeToNum(since_time)
        if before_time:
            before_time = _convertTimeToNum(before_time)
        self.notifier.nVersion()
        self.notifier.nRestore(False, self.username, fn)
        self.connection.connect()

        storage = EmailStorage.createStorage(fn, self.notifier)

        dates = set()
        for msg_fn, msg in storage.iterBackups(since_time, before_time):
            try:
                msg_date = _getMailIMAPDate(msg)
                msg_date2 = _getMailDate(msg)
                msg_iid = _getMailInternalId(msg)
                self.connection.append(self.connection.ALL_MAILS, "(\Seen)", msg_date, msg)

                dates.add(msg_date2)
            except:
                self.notifier.handleError(_("Error while restoring e-mail"))

        if dates:
            min_date, max_date = _shiftDates(min(dates), max(dates))
            min_date = imaplib.Time2Internaldate(min_date)
            max_date = imaplib.Time2Internaldate(max_date)
            assignment = storage.getLabelAssignment()
            self.restoreLabels(assignment, min_date, max_date)
        self.notifier.nRestore(True, self.username, fn)

    def clear(self):
        self.notifier.nVersion()
        self.notifier.nClear(False, self.username)
        self.connection.connect()

        self.connection.select(self.connection.ALL_MAILS)

        data = self.connection.search(['ALL'])
        nums = ','.join(data)
        if nums:
            self.connection.copy(nums, self.connection.TRASH)
            self.connection.store(nums, 'FLAGS.SILENT', '\\Deleted')
            self.connection.expunge()

        self.connection.select(self.connection.TRASH)
        data = self.connection.search(['ALL'])
        if nums:
            nums = ','.join(data)
            self.connection.store(nums, 'FLAGS.SILENT', '\\Deleted')
            self.connection.expunge()

        for label in self.getLabels():
            self.connection.delete(label)

        self.connection.close()
        self.notifier.nClear(True, self.username)

    def list(self):
        self.connection.connect(noguess=True)

        ret = self.connection.list()

        for i in ret:
            match = re.match(r'^\(.*\)\s".*"\s"(.*)"\s*$', i)
            box = match.groups(1)[0]

            self.connection.select(box)
            try:
                data = self.connection.search(['ALL'])
                num = len(data)
            except imaplib.IMAP4.error:
                num = -1
            yield box, num

    def isNewVersion(self):
        try:
            fr = urllib.urlopen(VERSION_URL)
            try:
                data = fr.read()
                url = 'http://code.google.com/p/gmail-backup-com/downloads/list'
                version_match = re.search('<td class="id"><a href=".*?">r(\d+)</a></td>', data)
                if version_match:
                    try:
                        new_revision = int(version_match.group(1))
                        if new_revision > int(GMB_REVISION):
                            return new_revision, url
                    except ValueError:
                        pass
                return None, None
            finally:
                fr.close()
        except:
            return None, None

    def reportNewVersion(self):
        version, url = self.isNewVersion()
        if version:
            msg = _('New version of GMail Backup is available!\nYou can download version %s here:\n%s') % (version, url)
        else:
            msg = _("You are using the latest version of GMail Backup.")
        self.notifier.nLog(msg)
        return version
