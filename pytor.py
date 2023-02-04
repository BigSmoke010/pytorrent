import wx
import libtorrent as lt
import time
import datetime
import threading
from pubsub import pub
from wx.lib.agw import ultimatelistctrl as ULC
import sqlite3
import os
import shutil
import difflib

class torthread(threading.Thread):
    def __init__(self, args, win):
        super().__init__(args=args, kwargs=win )
        pub.subscribe(self.deletetorrent, 'deletetor')
        pub.subscribe(self.pausetorrent, 'pausetor')
        self.start()
    def run(self):
        self.db = sqlite3.connect('downloads.db')
        self.curs = self.db.cursor()
        self.curs.execute('SELECT * FROM downloads')
        self.paused = False
        self.resumed = True
        self.deleted = False
        try:
            if self._args[5] == 'yes':
                self.paused = True
                self.resumed = False
        except IndexError:
            pass
        self.alls = self.curs.fetchall()
        self.curs.close()
        self.db.close()
        tmplist = []
        self.parseduri = lt.parse_magnet_uri(self._args[3])
        self.parseduri.save_path = self._args[4]
        for i in self.alls:
            tmplist.append(i[0])
        if self.parseduri.name in tmplist:
            try :
                with open('resumedata/' + self.parseduri.name.replace("/", "."), 'rb') as self.r:
                    self.rsumedata = lt.read_resume_data(self.r.read()) 
                    self.rsumedata.save_path = self._args[4] 
                    self.added = s.add_torrent(self.rsumedata)
            except FileNotFoundError:
                self.added = s.add_torrent(self.parseduri)
        else:
            self.added = s.add_torrent(self.parseduri)
            pub.sendMessage('add', args=[self.parseduri.name, datetime.datetime.now(), self._args[3], self._args[4], 'no'])
        while self.added.status() and not self.deleted:
            self.se = self.added.status()
            if self.deleted:
                self.added.pause()
            if self.paused and not self.resumed:
                self.added.pause()
            if self.resumed and not self.paused:
                self.added.resume()
            wx.PostEvent(self._kwargs, ResultEvent([self.se.progress * 100 ,self.se.num_seeds, self.se.num_peers, self.se.download_rate / 1000000, self.se.upload_rate / 1000000, self.se.state,self.parseduri.name, self.se.total / 1000000, self.se.total_done / 1000000]))
            time.sleep(3)

    def deletetorrent(self, args):
        if self.parseduri.name == args[0]:
            s.remove_torrent(self.added)
            # os.remove('resumedata/' + self.parseduri.name.replace("/","."))
            self.deleted = True
            try:
                shutil.rmtree(args[1])
            except NotADirectoryError:
                os.remove(args[1])

    def pausetorrent(self, args):
        if self.parseduri.name == args:
            self.paused = not self.paused
            self.resumed = not self.resumed

class magntdialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.InitUi()
    def InitUi(self):
        self.panel = wx.Panel(self)
        gridsizr = wx.GridSizer(1,2,1,1)
        stbx = wx.StaticBox(self.panel,-1,'Submit Magnet Link')
        sttcbx = wx.StaticBoxSizer(stbx, wx.VERTICAL)
        self.entry = wx.TextCtrl(self.panel,size=(250,30))
        self.entry2 = wx.TextCtrl(self.panel, size=(200, 30), value='./downloads/')
        self.pathbutton = wx.Button(self.panel, -1, 'Select Path')
        self.magnetbutton = wx.Button(self.panel, -1, 'Submit')
        sttcbx.Add(self.entry, 0, wx.ALIGN_CENTER)
        sttcbx.Add(self.magnetbutton, 0, wx.ALIGN_CENTER)
        stbx2 = wx.StaticBox(self.panel,-1, 'Path', size=(300,200))
        sttcbx2 = wx.StaticBoxSizer(stbx2)
        sttcbx2.Add(self.pathbutton)
        sttcbx2.Add(self.entry2)
        gridsizr.Add(sttcbx, 0, wx.ALIGN_LEFT)
        gridsizr.Add(sttcbx2, 0, wx.ALIGN_RIGHT)
        self.panel.SetSizer(gridsizr)
        self.panel.Bind(wx.EVT_BUTTON, self.getmagnet, self.magnetbutton)
        self.panel.Bind(wx.EVT_BUTTON, self.setpath, self.pathbutton)

    def getmagnet(self, event):
        pub.sendMessage('addfromdiag', x=[None, None, None,self.entry.GetValue(), self.entry2.GetValue()])
        magntdialog.Destroy(self)

    def setpath(self, event):
        filepath = wx.DirDialog(None, 'Select Folder', './downloads/', wx.DD_DEFAULT_STYLE)
        filepath.ShowModal()
        filepath.Destroy()
        self.entry2.SetValue(filepath.GetPath())

class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(-1)
        self.data = data

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.db =sqlite3.connect('downloads.db')
        self.cur = self.db.cursor()
        self.db.commit()
        self.cur.execute('CREATE TABLE IF NOT EXISTS downloads (name, date, link, path, paused)')
        self.panel = wx.Panel(self)
        self.boxsizer = wx.BoxSizer(wx.VERTICAL)
        self.indeex = 0
        self.ult = ULC.UltimateListCtrl(self.panel, agwStyle= ULC.ULC_REPORT | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Name"
        self.ult.InsertColumnInfo(0, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Total Download"
        self.ult.InsertColumnInfo(1, info)
        info._text = "Progress"
        self.ult.InsertColumnInfo(2, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Total Downloaded"
        self.ult.InsertColumnInfo(3, info)
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Status"
        self.ult.InsertColumnInfo(4, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Seeds"
        self.ult.InsertColumnInfo(5, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Peers"
        self.ult.InsertColumnInfo(6, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Download Speed"
        self.ult.InsertColumnInfo(7, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Upload Speed"
        self.ult.InsertColumnInfo(8, info)
        self.ult.SetColumnWidth(0, 250)
        self.ult.SetColumnWidth(7, 150)
        self.ult.SetColumnWidth(2, 150)
        self.ult.SetColumnWidth(3, 150)
        self.ult.SetColumnWidth(4, 100)
        self.ult.SetColumnWidth(5, 80)
        self.ult.SetColumnWidth(6, 80)
        self.ult.SetColumnWidth(1, 100)
        self.ult.SetColumnWidth(8, 100)
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.cur.close()
        self.db.close()
        for i in self.alldowns:
            torthread(i, self)
            self.ult.InsertStringItem(i[0], i[1])
        self.boxsizer.Add(self.ult, 1, wx.EXPAND)
        self.panel.SetSizer(self.boxsizer)
        pub.subscribe(self.addtor, 'add')
        pub.subscribe(self.addfrmdiag, 'addfromdiag')
        self.EVT_RESULT(self, self.updateprog)
        self.showmenu()
        self.Bind(wx.EVT_MENU, self.magnet, self.frstentry)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRight)

    def EVT_RESULT(self, win, func):
        """Define Result Event."""
        win.Connect(-1, -1, -1, func)

    def OnRight(self, event):
        popupmenu = wx.Menu()
        PauseResume = popupmenu.Append(-1, "Pause/Resume")
        Delete = popupmenu.Append(-1, 'Delete With Files')
        self.Bind(wx.EVT_MENU, self.OnPause, PauseResume)
        self.Bind(wx.EVT_MENU, self.OnDelete, Delete)
        self.ult.PopupMenu(popupmenu)

    def OnPause(self, event):
        self.db = sqlite3.connect('downloads.db') 
        self.cur = self.db.cursor()
        self.cur.execute('SELECT * FROM downloads')
        self.all = self.cur.fetchall()
        ind = self.ult.GetFirstSelected()
        pub.sendMessage('pausetor', args=self.all[ind][0])
        if self.all[ind][-1] == 'yes': 
            self.cur.execute('UPDATE downloads SET paused = :nai WHERE oid =' + str(ind + 1),
                             {
                                'nai' : 'no'
                             })
        else:
            self.cur.execute('UPDATE downloads SET paused = :nai WHERE oid =' + str(ind + 1),
                             {
                                'nai' : 'yes'
                             })

        self.db.commit()
        self.cur.close()
        self.db.close()

    def OnDelete(self, event):
        self.ind = self.ult.GetFirstSelected()
        self.db = sqlite3.connect('downloads.db')
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        pub.sendMessage('deletetor', args=[self.alldowns[self.ind][1], self.alldowns[self.ind][4]])
        self.cur.execute('DELETE FROM downloads WHERE oid =' + str(self.ind + 1))
        self.cur.execute('UPDATE downloads SET oid = oid - 1')
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.ult.DeleteItem(self.ind)
        self.db.commit()
        self.cur.close()
        self.db.close()

    def showmenu(self):
        self.frstmenu = wx.Menu()
        self.frstentry = self.frstmenu.Append(0, item='Add Magnet')
        self.scndentry = self.frstmenu.Append(1, item='Open .torrent')
        self.mainmenu = wx.MenuBar()
        self.mainmenu.Append(self.frstmenu, 'Open')
        self.SetMenuBar(self.mainmenu)

    def magnet(self, event):
        dilaog = magntdialog(None, title='Add magnet', size=(560,130))
        dilaog.ShowModal()
        dilaog.Destroy()

    def updateprog(self, message):
        for x,y in enumerate(self.alldowns):
            if y[1] == message.data[6]:
                self.ult.SetStringItem(x, 2, str(message.data[0]))
                self.ult.SetStringItem(x, 4, str(message.data[5]))
                self.ult.SetStringItem(x, 5, str(message.data[1]))
                self.ult.SetStringItem(x, 6, str(message.data[2]))
                self.ult.SetStringItem(x, 7, str(round(message.data[3], 1)) + 'MB')
                self.ult.SetStringItem(x, 8, str(message.data[4]) + 'MB')
                self.ult.SetStringItem(x, 1, str(round(message.data[7], 2)) + 'MB')
                self.ult.SetStringItem(x, 3, str(round(message.data[8], 2)) + 'MB')
    def addtor(self,args):
        self.db =sqlite3.connect('downloads.db')
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        tmplist = []
        ls = os.listdir(args[3])
        for im in self.alldowns:
            tmplist.append(im[0])
        if args[0] in tmplist:
            print('torrent already in')
        else:
            self.cur.execute('INSERT INTO downloads VALUES (:torname,:tordate,:link, :path, :ispaused)',
            {
                'torname': args[0],
                'tordate': args[1],
                'link': args[2],
                'path': ls[0], 
                'ispaused': args[4]
            }
            )
            try:
                self.ult.InsertStringItem(self.alldowns[-1][0], args[0])
            except IndexError:
                self.ult.InsertStringItem(0, args[0])

        self.db.commit()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.cur.close()
        self.db.close()
    def addfrmdiag(self, x):
        torthread(x, self)


class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        frame = MyFrame(parent=None, title='pyTorrent', size=(1100, 350))
        frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()
