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
        self.unit = 'MB'
        self.doneunit = 'MB'
        self.total = 0
        self.total_done = 0
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
        try: 
            self.parseduri = lt.parse_magnet_uri(self._args[3])
        except Exception as e:
            pub.sendMessage('error', msg=e)

        self.parseduri.save_path = self._args[4]
        for i in self.alls:
            tmplist.append(i[0])
        if self.parseduri.name in tmplist:
            try:
                with open('resumedata/' + self.parseduri.name, 'rb') as self.r:
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
            with open ('resumedata/' + self.parseduri.name, 'wb') as f:
                f.write(lt.write_resume_data_buf(lt.parse_magnet_uri(self._args[3])))
            if self.se.total >= 1000000000:
                self.total= self.se.total / 1000000000
                self.unit = 'GB'
            else:
                self.total = self.se.total / 1000000 
                self.unit = 'MB'
            if self.se.total_done >= 1000000000:
                self.total_done= self.se.total_done / 1000000000
                self.doneunit = 'GB'
            else:
                self.total_done = self.se.total_done / 1000000 
                self.doneunit = 'MB'
            wx.PostEvent(self._kwargs, ResultEvent([self.se.progress * 100 ,self.se.num_seeds, self.se.num_peers, self.se.download_rate / 1000000, self.se.upload_rate / 1000000, self.se.state,self.parseduri.name, self.total , self.total_done, self.unit, self.doneunit]))
            time.sleep(3)

    def deletetorrent(self, args):
        if self.parseduri.name == args[0]:
            s.remove_torrent(self.added)
            os.remove('resumedata/' + self.parseduri.name)
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
        for index, i in enumerate(['Name', 'Size', 'Progress', 'Downloaded', 'Status', 'Down Speed', 'Up Speed','Seeds', 'Peers']):
            info = ULC.UltimateListItem()
            info._mask = wx.LIST_MASK_TEXT
            info._text = i
            self.ult.InsertColumnInfo(index, info)

        for index, i in enumerate([250, 110, 150,110,100, 80,80,100,100]):
            self.ult.SetColumnWidth(index, i)
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.cur.close()
        self.db.close()
        self.allgauges = []
        for i in self.alldowns:
            if i[-1] != 'yes':
                self.allgauges.append((i[1],wx.Gauge(self.ult)))
                torthread(i, self)
                self.ult.InsertStringItem(i[0], i[1])

        self.updategauges(self.allgauges)
        self.boxsizer.Add(self.ult, 1, wx.EXPAND)
        self.panel.SetSizer(self.boxsizer)
        pub.subscribe(self.addtor, 'add')
        pub.subscribe(self.addfrmdiag, 'addfromdiag')
        pub.subscribe(self.raiseerror, 'error')
        self.EVT_RESULT(self, self.updateprog)
        self.showmenu()
        self.Bind(wx.EVT_MENU, self.magnet, self.frstentry)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRight)

    def updategauges(self, gauges):
            for x, gaug in enumerate(gauges):
                try:
                    self.ult.SetItemWindow(x, 2,  gaug[1], expand=True)
                except AttributeError:
                    pass

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
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        del self.allgauges[self.ind]
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
        dilaog = magntdialog(None, title='Add magnet', size=(660,230))
        dilaog.ShowModal()
        dilaog.Destroy()

    def updateprog(self, message):
        self.db =sqlite3.connect('downloads.db')
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        for x,y in enumerate(self.alldowns):
            if y[1] == message.data[6]:
                for name,gaug in self.allgauges:
                    if name == message.data[6]:
                        gaug.SetValue(int(message.data[0]))
                self.ult.SetStringItem(x, 4, str(message.data[5]))
                self.ult.SetStringItem(x, 7, str(message.data[1]))
                self.ult.SetStringItem(x, 8, str(message.data[2]))
                self.ult.SetStringItem(x, 5, str(round(message.data[3], 1)))
                self.ult.SetStringItem(x, 6, str(round(message.data[4], 1)))
                self.ult.SetStringItem(x, 1, str(round(message.data[7], 2))+ message.data[9])
                self.ult.SetStringItem(x, 3, str(round(message.data[8], 2))+ message.data[10])
    def addtor(self,args):
        self.db =sqlite3.connect('downloads.db')
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        tmplist = []
        ls = os.listdir(args[3])
        while ls == []:
            ls = os.listdir(args[3])
            time.sleep(3)
        for im in self.alldowns:
            tmplist.append(im[0])
        if args[0] not in tmplist:
            self.cur.execute('INSERT INTO downloads VALUES (:torname,:tordate,:link, :path, :ispaused)',
            {
                'torname': args[0],
                'tordate': args[1],
                'link': args[2],
                'path': args[3] + ls[0], 
                'ispaused': args[4]
            }
            )
            try:
                self.ult.InsertStringItem(self.alldowns[-1][0], args[0])
            except IndexError:
                self.ult.InsertStringItem(0, args[0])

            self.allgauges.append((args[0], wx.Gauge(self.ult)))
            self.updategauges(self.allgauges)
            self.db.commit()
            self.cur.close()
            self.db.close()

    def addfrmdiag(self, x):
        torthread(x, self)

    def raiseerror(self, msg):
        dig = wx.MessageDialog(None, str(msg), 'Error', wx.ICON_ERROR )
        dig.ShowModal()


class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        frame = MyFrame(parent=None, title='pyTorrent', size=(1100, 350))
        frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()
