#!/usr/bin/env python
# -*-  coding: utf-8 -*-
#   
#   Gmail Backup GUI
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
import wx, sys, optparse
import xml.dom.minidom
import threading
import time
import imaplib

import wx
import wx.html
import wx.lib.dialogs
import wx.lib.newevent


import gmb as gmail_backup

import locale

import ctypes
import gettext

import pickle

GMB_GUI_REVISION = u'-Revision: 12345 -'
GMB_GUI_DATE = u'-Date: 2017-07-12 -'

GMB_GUI_REVISION = GMB_GUI_REVISION[11:-2]
GMB_GUI_DATE = GMB_GUI_DATE[7:-2].split()[0]
 
MAX_REVISION = str(max(int(GMB_GUI_REVISION), int(gmail_backup.GMB_REVISION)))
MAX_DATE = max(GMB_GUI_DATE, gmail_backup.GMB_DATE)

if os.name == 'nt':
    lang = locale.getdefaultlocale()[0]
    os.environ['LANGUAGE'] = lang

MESSAGES_DIR = os.path.join(os.path.dirname(sys.argv[0]), 'messages')
gettext.install('gmail-backup', MESSAGES_DIR, unicode=1)

(UpdateLogEvent, EVT_UPDATE_LOG) = wx.lib.newevent.NewEvent()

class GUINotifier(gmail_backup.ConsoleNotifier):
    def __init__(self, mainwindow):
        super(GUINotifier, self).__init__()
        self.mw = mainwindow
        self.last_update_time = 0

    def createEvent(self, msg, force=False):
        now = time.time()
        if now - self.last_update_time < 1 and not force:
            return
        else:
            if not force:
                self.last_update_time = now
            evt = UpdateLogEvent(msg = msg, speed=self.getSpeed(),
                    total=self.getTotal(), percentage=self.getPercentage())
            return evt

    def uprint(self, msg):
        evt = self.createEvent(msg, force=True)
        if evt is not None:
            wx.PostEvent(self.mw, evt)

    def uprint2(self, msg):
        pass

    def updateSpeed(self):
        evt = self.createEvent(None)
        if evt is not None:
            wx.PostEvent(self.mw, evt)

class InterruptableThread(threading.Thread):
    @classmethod
    def _async_raise(cls, tid, excobj):
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
        if res == 0:
            raise ValueError("nonexistent thread id")
        elif res > 1:
            # """if it returns a number greater than one, you're in trouble, 
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")
     
    def raise_exc(self, excobj):
        assert self.isAlive(), "thread must be started"
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._async_raise(tid, excobj)
                return
        
        # the thread was alive when we entered the loop, but was not found 
        # in the dict, hence it must have been already terminated. should we raise
        # an exception here? silently ignore?
    
    def terminate(self):
        # must raise the SystemExit type, instead of a SystemExit() instance
        # due to a bug in PyThreadState_SetAsyncExc
        self.raise_exc(SystemExit)

class ThreadedGMailBackup(gmail_backup.GMailBackup):
    def _runThread(self, method, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except:
            type, error, tb = sys.exc_info()
            self.notifier.nException(type, error, tb)

    def backup(self, *args, **kwargs):
        t = InterruptableThread(target=self._runThread, args=(gmail_backup.GMailBackup.backup,)+args, kwargs=kwargs)
        t.start()
        return t

    def restore(self, *args, **kwargs):
        t = InterruptableThread(target=self._runThread, args=(gmail_backup.GMailBackup.restore,)+args, kwargs=kwargs)
        t.start()
        return t

    def reportNewVersion(self, *args, **kwargs):
        t = InterruptableThread(target=self._runThread, args=(gmail_backup.GMailBackup.reportNewVersion,)+args, kwargs=kwargs)
        t.start()
        return t

TITLE_IDLE = _('Gmail Backup')
TITLE_WORKING = _('(%.1f%%) Gmail Backup')

class MainPanel(wx.Panel):
    def __init__(self, *args, **kwargs):

        self._prevLocale = 'C'
        
        wx.Panel.__init__(self, *args, **kwargs)

        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        self.SetBackgroundColour(colour)

        logo = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(os.path.join(os.path.dirname(sys.argv[0]), 'gmb.gif')))

        self.revision    = wx.StaticText(self, -1, _("revision %s (%s)") % (MAX_REVISION, MAX_DATE))
   
        stGmailLogin    = wx.StaticText(self, -1, _("Gmail login:\n(full email address)"))
        self.login      = wx.TextCtrl(self, -1, size=(300,-1))

        stGnailPassword = wx.StaticText(self, -1, _("Gmail password:"))
        self.password   = wx.TextCtrl(self, -1, size=(300,-1),  style=wx.TE_PASSWORD)

        stBckpFldr      = wx.StaticText(self, -1, _("Backup folder:"))
        self.folder     = wx.TextCtrl(self, -1, size=(300,-1))
        self.folder.SetToolTipString( \
_('''You can use following forms:
  directory
  filename.zip
  directory#template
  filename.zip#template

In the template you can use following variables, which will be substituted with values in the stored message:
  $YEAR, $MONTH, $DAY
  $HOUR, $MINUTE, $SECOND
  $FROM, $SUBJ

You can write them either as $YEAR or ${YEAR}.'''))
        self.btnSlctFolder   = wx.Button(self, -1, _("&Directory"))

        if os.name == 'posix':
            self.onlyNewest = wx.CheckBox(self, -1, label=_("Newest\nemails\nonly"))
        else:
            self.onlyNewest = wx.CheckBox(self, -1, label=_("Newest emails only"))
        self.onlyNewest.SetValue(True)
        
        stSince         = wx.StaticText(self, -1, _("Since date:"))
        self.since      = wx.DatePickerCtrl(self, -1, size=(300, -1))
        self.since.Disable()
        
        stBefore          = wx.StaticText(self, -1, _("Before date:"))
        self.before       = wx.DatePickerCtrl(self, -1, size=(300, -1))
        self.before.Disable()
        
        line1           = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        self.log        = wx.TextCtrl(self, -1, size=(600,150),  style=wx.TE_MULTILINE|wx.TE_WORDWRAP|wx.TE_READONLY|wx.HSCROLL|wx.VSCROLL|wx.ALWAYS_SHOW_SB)
        self.progress   = wx.Gauge(self, -1, size=(300,10), style=wx.GA_HORIZONTAL)
        self.progress.SetRange(100)
        self.message    = wx.StaticText(self, -1, size=(300,-1), style=wx.ALIGN_LEFT)
        line2           = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)

        # buttons
        self.btnBackup   = wx.Button(self, wx.ID_OK,  _('&Backup'))
        self.btnRestore  = wx.Button(self,  -1,  _("&Restore"))
        self.btnStop     = wx.Button(self,  -1,  _("Stop"))
        self.btnStop.Disable()
        #btnHelp     = wx.Button(self,  wx.ID_HELP)
        #btnAbout    = wx.Button(self,  wx.ID_ABOUT)
        self.btnNewVer   = wx.Button(self,  -1,  _("New Versions"))
        self.btnExit     = wx.Button(self,  wx.ID_EXIT, _('Quit'))
        
        szrGBS = wx.GridBagSizer(15, 15)
        szrGBS.Add(stGmailLogin, (1, 1))
        szrGBS.Add(self.login, (1, 2))                

        szrGBS.Add(stGnailPassword, (2, 1))
        szrGBS.Add(self.password, (2, 2))       

        szrGBS.Add(stBckpFldr, (3, 1))
        szrGBS.Add(self.folder, (3, 2))       
        szrGBS.Add(self.btnSlctFolder, (3, 3))       
    
        szrGBS.Add(self.onlyNewest, (4, 3), (2, 1), wx.ALIGN_CENTER_VERTICAL)
        szrGBS.Add(stSince, (4, 1))
        szrGBS.Add(self.since, (4, 2))
        szrGBS.Add(stBefore, (5, 1))
        szrGBS.Add(self.before, (5, 2))
        
        szrHorizontal3 = wx.BoxSizer(wx.HORIZONTAL)
        szrHorizontal3.Add(self.btnBackup, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        szrHorizontal3.Add(self.btnRestore, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        szrHorizontal3.Add(self.btnStop, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        szrHorizontal3.Add(self.btnNewVer, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        szrHorizontal3.Add(self.btnExit, 0, wx.ALIGN_CENTER|wx.LEFT, 55)

        szrHorizontal5 = wx.BoxSizer(wx.HORIZONTAL)
        szrHorizontal5.Add(self.message, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 0)     
        szrHorizontal5.Add(self.progress, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0)
        
        szrHorizontal4 = wx.BoxSizer(wx.VERTICAL)
        szrHorizontal4.Add(self.log, 0, wx.ALIGN_LEFT, 30)     
        szrHorizontal4.Add(szrHorizontal5, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 0)

        szrVertical = wx.BoxSizer(wx.VERTICAL)
        szrVertical.Add(logo, 0, wx.ALIGN_CENTER|wx.TOP, 25)
        szrVertical.Add(self.revision, 0, wx.ALIGN_CENTER|wx.BOTTOM, 0)
        
        szrVertical.Add(szrGBS, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        szrVertical.Add(line1, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)     
        szrVertical.Add(szrHorizontal4, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 15)
        szrVertical.Add(line2, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)     
        szrVertical.Add(szrHorizontal3, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 15)
        
        self.btnSlctFolder.Bind(wx.EVT_BUTTON, self.OnSelectDir)
        self.btnBackup.Bind(wx.EVT_BUTTON, self.OnBackup)   
        self.btnBackup.SetDefault()
        self.btnRestore.Bind(wx.EVT_BUTTON, self.OnRestore)   
        self.btnStop.Bind(wx.EVT_BUTTON, self.OnStop)   
#        btnAbout.Bind(wx.EVT_BUTTON, self.OnAbout)   
#        btnHelp.Bind(wx.EVT_BUTTON, self.OnHelp)   
        self.btnNewVer.Bind(wx.EVT_BUTTON, self.OnNewVer)   
        self.btnExit.Bind(wx.EVT_BUTTON, self.OnExit)   
        self.Bind(EVT_UPDATE_LOG, self.OnLogAppend)   
        self.onlyNewest.Bind(wx.EVT_CHECKBOX, self.OnOnlyNewest)
        
        self.Refresh()
        self.SetSizer(szrVertical)
        self.SetAutoLayout(True)
        szrVertical.Fit(self)
        self.Centre();

        self.enableCntrls()

        self._clearLocale()

        self.currentThread = None
        self.notifier = GUINotifier(self)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimerRunning)

        #self.SetDefaultItem(self.btnBackup)
        
        self.restoreSettings()

    def _clearLocale(self):
        self._prevLocale = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, 'C')

    def _restoreLocale(self):
        locale.setlocale(locale.LC_TIME, self._prevLocale)

    def disableCntrls(self):
        self.login.Disable()
        self.password.Disable()
        self.folder.Disable()
        self.btnSlctFolder.Disable()
        self.onlyNewest.Disable()
        self.since.Disable()
        self.before.Disable()
        self.btnBackup.Disable()
        self.btnRestore.Disable()
        self.btnNewVer.Disable()
        self.btnExit.Disable()
        
        self.progress.Enable()
        self.message.Enable()
        
        return

    def enableCntrls(self):
        self.login.Enable()
        self.password.Enable()
        self.folder.Enable()
        self.btnSlctFolder.Enable()
        self.onlyNewest.Enable()

        self.enableDates()

        self.btnBackup.Enable()
        self.btnRestore.Enable()
        self.btnNewVer.Enable()
        self.btnExit.Enable()

        self.progress.Disable()
        self.message.Disable()

        self.password.SetFocus()
        return

    def enableDates(self):
        if self.onlyNewest.GetValue():
            self.since.Disable()
            self.before.Disable()
        else:
            self.since.Enable()
            self.before.Enable()
            
    def saveSettings(self):
        settings["login"] = self.login.GetValue()
        settings["folder"] = self.folder.GetValue()
        settings["onlyNewest"] = str(self.onlyNewest.GetValue())
        settings["since"] = str(self.since.GetValue().FormatISODate())
        settings["before"] = str(self.before.GetValue().FormatISODate())

        saveSettings()
        
        return
    
    def restoreSettings(self):
        #read and set
        self.login.SetValue(settings["login"].strip())
        self.folder.SetValue(settings["folder"].strip())
        
        if settings["onlyNewest"].strip() == "True":
            self.onlyNewest.SetValue(True)
            self.since.Disable()
            self.before.Disable()
        else:
            self.onlyNewest.SetValue(False)
            self.since.Enable()
            self.before.Enable()
        
        try:
            self.since.SetValue(self.readDate(settings["since"]))
            self.before.SetValue(self.readDate(settings["before"]))
        except:
            pass
            
        return

    def readDate(self, snc):
        d = wx.DateTime()
        snc = snc.strip()
#        print snc
        d.ParseDate(snc)
#        d.Set(int(snc[2]), int(snc[1]), int(snc[0]), 1, 1, 1, 1)
#        print str(d)
        
        return d
        
    def validateInputData(self):
        error = ""
        if not self.login.GetValue():
            error += _("Enter valid email adress which you want to backup.\n")
        if not self.password.GetValue():
            error += _("Enter valid password for your gmail account.\n")
        if not self.folder.GetValue():
            error += _("Enter folder where you want to store your emails.\n")
        
        if error:
            dlg = wx.MessageDialog(self, error, _("Invalid input data"),  style = wx.CANCEL|wx.ICON_ERROR)
            dlg.ShowModal()
            return True
            
        return False
        
    def OnLogAppend(self, event):
        if event.msg is not None:
            msg = '%s\n' % event.msg
            self.log.AppendText(msg)
        if event.percentage is not None:
            self.progress.SetValue(event.percentage)
        else:
            self.progress.SetValue(0)
        label = _('Processed %.2fMB, speed %.1fKB/s') % (event.total, event.speed)
        self.message.SetLabel(label)
        if event.percentage is not None:
            self.SetLabel(TITLE_WORKING % (event.percentage,))

    def OnSelectDir(self, event):
        dir = os.path.abspath(self.folder.GetValue().strip())
        
        dlg = wx.DirDialog(self, _("Select a directory for Gmail Backup"), dir, size = (400, 600))
        if dlg.ShowModal() == wx.ID_OK:
            dir = dlg.GetPath()
            self.folder.SetValue(dir)
        dlg.Destroy()

    def convertTime(self, value):
        year = value.GetYear()
        month = value.GetMonth()+1 # Are month numbers in range 0..11?
        day = value.GetDay()
        t = '%04d%02d%02d' % (year, month, day)
        t = time.mktime(time.strptime(t, '%Y%m%d'))
        return imaplib.Time2Internaldate(t)

    def convertTimeRestore(self, value):
        year = value.GetYear()
        month = value.GetMonth()+1 # Are month numbers in range 0..11?
        day = value.GetDay()
        t = '%04d%02d%02d' % (year, month, day)
        return t

    def OnBackup(self, event):
        if self.validateInputData():
            return
        
        username = self.login.GetValue()
        password = self.password.GetValue()
        dirname = self.folder.GetValue()
        where = ['ALL']

        if self.onlyNewest.GetValue():
            stamp = True
        else:    
            stamp = False
            if self.since.GetValue():
                since = self.convertTime(self.since.GetValue())
                where.append('SINCE')
                where.append(since)
            if self.before.GetValue():
                before = self.convertTime(self.before.GetValue())
                where.append('BEFORE')
                where.append(before)

        b = ThreadedGMailBackup(username, password, self.notifier)
        self.currentThread = b.backup(dirname, where, stamp=stamp)

        # desable all necessary controls
        self.disableCntrls()
        self.btnStop.Enable()
        self.timer.Start(200)
        
        self.saveSettings()

        return True

    def OnTimerRunning(self, event):
        if not self.currentThread.isAlive():
            self.SetLabel(TITLE_IDLE)
            self.enableCntrls()
            self.btnStop.Disable()
            self.timer.Stop()

        return True

    def OnOnlyNewest(self,  event):
        self.enableDates()
            
        return True
        
    def OnRestore(self, event):
        if self.validateInputData():
            return

        since = before = None
        if not self.onlyNewest.GetValue():
            if self.since.GetValue():
                since = self.convertTimeRestore(self.since.GetValue())
            if self.before.GetValue():
                before = self.convertTimeRestore(self.before.GetValue())

            
        username = self.login.GetValue()
        password = self.password.GetValue()
        dirname = self.folder.GetValue()
        b = ThreadedGMailBackup(username, password, self.notifier)
        self.currentThread = b.restore(dirname, since, before)
        
        # desable all necessary controls
        self.disableCntrls()
        self.btnStop.Enable()
        self.timer.Start(200)
        
        self.saveSettings()

        return True
    
    def OnStop(self, event):
        try:
            if self.currentThread is not None:
                self.notifier.nLog(_("Interrupting ..."))
                self.currentThread.raise_exc(KeyboardInterrupt)
                
        except AssertionError:
            pass
        return True
    
    def OnNewVer(self, event):
        b = ThreadedGMailBackup(None, None, self.notifier)
        self.currentThread = b.reportNewVersion()
        
        # desable all necessary controls
        self.disableCntrls()
        self.btnStop.Enable()
        self.timer.Start(200)

        return True

    def OnExit(self, event):
        self.OnStop(event)
        self.saveSettings()
        
        self.GetParent().Close()
        
        return True

class MainDialog(wx.Frame):
    def __init__(self, parent, ID, title, 
        size=wx.DefaultSize, 
        pos=wx.DefaultPosition, 
        style=(wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX) | wx.TAB_TRAVERSAL):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style = style)

        icon = wx.Icon(os.path.join(os.path.dirname(sys.argv[0]), 'gmb.ico'), wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        # now create a panel (between menubar and statusbar) ...
        self.panel = MainPanel(self, -1)

        # create a create menu
        self.menuBar = wx.MenuBar()
        self.menuCommands = wx.Menu()
        self.menuHelp = wx.Menu()

        self.menuCommands.Append(10003, _("&Stop"), _("Stop backing up or restoring emails"))
        self.Bind(wx.EVT_MENU, self.panel.OnStop, id=10003)
        self.menuCommands.AppendSeparator()
        self.menuCommands.Append(wx.ID_EXIT, _("&Quit"), _("Terminate the program"))
        self.Bind(wx.EVT_MENU, self.panel.OnExit, id=wx.ID_EXIT)

        self.menuHelp.Append(10001, _("&Check new versions"), _("Check new versions of this program"))
        self.Bind(wx.EVT_MENU, self.panel.OnNewVer, id=10001)
        
        self.menuHelp.Append(wx.ID_ABOUT, _("&About"), _("More information about this program"))
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        
        self.menuBar.Append(self.menuCommands, _("&Commands"));
        self.menuBar.Append(self.menuHelp, _("&Help"));
        self.SetMenuBar(self.menuBar)
        
        # create a status bar at the bottom of the frame
        self.CreateStatusBar()
        
        szrVertical = wx.BoxSizer(wx.VERTICAL)
        szrVertical.Add(self.panel, 0, wx.EXPAND|wx.EXPAND)

        self.Refresh()
        self.SetSizer(szrVertical)
        self.SetAutoLayout(True)
        szrVertical.Fit(self)
        self.Centre();
        
    def OnAbout(self, event):
        dlg = AboutBox(MAX_REVISION, MAX_DATE)
        dlg.ShowModal()
        dlg.Destroy()  
        
        return True
        
    def OnHelp(self, event):
        return True
  
aboutText = """
<p align="center">
    <b>Gmail Backup</b> 
    <br>
    <br>
    revision %(revision)s (%(revisiondate)s)
</p>

<p>
The purpose of this program is to simplify 
the process of backing up, restoration, or  
migration of your emails from your Gmail Account.
</p>

<p>
Copyright (C) 2008-2011 by Jan Svec and Filip Jurcicek. 
<br>With a <a href="https://code.google.com/p/gmail-backup-com/issues/detail?id=16">bugfix</a> by Jesper Hertel 2013-07-03.
</p>

<p>
See <a href="http://code.google.com/p/gmail-backup-com/">http://code.google.com/p/gmail-backup-com/</a>
</p>
""" 

class HtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, id, size=(600,400)):
        wx.html.HtmlWindow.__init__(self,parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())
        

class AboutBox(wx.Dialog):
    def __init__(self,  MAX_REVISION, MAX_DATE):
        wx.Dialog.__init__(self, None, -1, "About Gmail Backup",
            style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.RESIZE_BORDER|
                wx.TAB_TRAVERSAL)

        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        self.SetBackgroundColour(colour)
        
        szrVertical = wx.BoxSizer(wx.VERTICAL)

        hwin = HtmlWindow(self, -1, size=(400,200))
        vers = {}
        vers["revision"] = MAX_REVISION
        vers["revisiondate"] = MAX_DATE
        hwin.SetPage(_(aboutText) % vers)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth()+25, irep.GetHeight()+20))
        self.SetClientSize(hwin.GetSize())

        self.btnOk = wx.Button(self,  wx.ID_OK,  _("Ok"))
        szrVertical.Add(hwin, 0, wx.ALIGN_CENTER|wx.ALL, 15)
        szrVertical.Add(self.btnOk, 0, wx.ALIGN_CENTER|wx.BOTTOM, 15)
        
        self.SetSizer(szrVertical)
        self.SetAutoLayout(True)
        szrVertical.Fit(self)

        self.CentreOnParent(wx.BOTH)
        self.SetFocus()

import collections

# in this dictionary we store all settings
settings = collections.defaultdict(str)

def settingsFn():
    """Generate a platform dependent config file."""
    c_dir = os.path.dirname(sys.argv[0])
    c_cfg = os.path.join(c_dir, 'gmail-backup-gui.cfg')
    if os.path.isfile(c_cfg):
        return c_cfg

    if os.name == 'nt':
        appdata = os.environ['APPDATA']
        fn = os.path.join(appdata, 'Gmail Backup')
    else:
        fn = os.path.expanduser(os.path.join('~', '.gmb'))
    fn = os.path.join(fn, 'settings')
    return fn

def settingsMakedirs():
    """Create needed directries to store the config file."""
    
    fn = settingsFn()
    dn = os.path.dirname(fn)
    if not os.path.isdir(dn):
        os.makedirs(dn)

def saveSettings():
    """Save the settings dictionary by pickle module."""
    
    try:
        settings_fn = settingsFn()
        settingsMakedirs()
        fl = open(settings_fn, "wb")
        pickle.dump(settings, fl)
        fl.close()
    except:
        pass
    
def loadSettings():
    """Load the settings dictionary by pickle module."""
    global settings
    
    try:
        settings_fn = settingsFn()
        settingsMakedirs()
        fl = open(settings_fn, "rb")
        settings = pickle.load(fl)
        fl.close()
    except:
        # no settings yet
        pass
       
        
#############################################################################
## test of dialogue
#############################################################################
if __name__ == "__main__":
    # load the settings when module is initialised
    loadSettings()
    
    app = wx.PySimpleApp()
    
    dlg = MainDialog(None, -1, TITLE_IDLE)
    dlg.Center()
    app.SetTopWindow(dlg)
    dlg.Show()

    app.MainLoop()
    
