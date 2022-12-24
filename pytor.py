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
    def __init__(self, args):
        super().__init__(args=args)
        pub.subscribe(self.deletetorrent, 'deletetor')
        pub.subscribe(self.pausetorrent, 'pausetor')
        self.start()

    def run(self):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.curs = self.db.cursor()
        self.curs.execute('SELECT * FROM downloads')
        self.paused = False
        self.resumed = True
        self.deleted = False
        self.alls = self.curs.fetchall()
        self.db.close()
        self.parseduri = lt.parse_magnet_uri(self._args[3])
        self.parseduri.save_path = self._args[4]
        tmplist = []
        for im in self.alls:
            tmplist.append(im[0])
        if self.parseduri.name in tmplist:
            try:
                with open('resumedata/' + self.parseduri.name, 'rb') as r:
                    resumedata = lt.read_resume_data(r.read())
                    resumedata.save_path = self._args[4]
                    self.added = s.add_torrent(resumedata)
            except FileNotFoundError:
                self.parseduri.save_path = self._args[4]
                self.added = s.add_torrent(self.parseduri)
        if self.parseduri.name not in tmplist:
            self.parseduri.save_path = self._args[4]
            self.added = s.add_torrent(self.parseduri)
        pub.sendMessage('add', args=[self.parseduri.name, datetime.datetime.now(), self._args[3], self._args[4]])

        while self.added.status().state != lt.torrent_status.seeding and not self.deleted:
            if self.paused and not self.resumed:
                self.added.pause()
            if self.resumed and not self.paused:
                self.added.resume()
            x = lt.write_resume_data_buf(lt.parse_magnet_uri(self._args[3]))
            with open ('resumedata/' + self.parseduri.name, 'wb') as f:
                f.write(x)
            se = self.added.status()
            progress = se.progress * 100
            time.sleep(5)
            pub.sendMessage('update', message=[progress,se.num_seeds,se.num_peers, se.download_rate / 1000000, se.upload_rate / 1000000, se.state,self.parseduri.name])
            tmplist.clear()

        while self.added.status().state == lt.torrent_status.seeding and not self.deleted:
            if self.paused and not self.resumed:
                self.added.pause()
            if self.resumed and not self.paused:
                self.added.resume()
            x = lt.write_resume_data_buf(lt.parse_magnet_uri(self._args[3]))
            with open ('resumedata/' + self.parseduri.name, 'wb') as f:
                f.write(x)
            se = self.added.status()
            progress = se.progress * 100
            time.sleep(5)
            pub.sendMessage('update', message=[progress,se.num_seeds,se.num_peers, se.download_rate / 1000000, se.upload_rate / 1000000, se.state,self.parseduri.name])
            tmplist.clear()

    def deletetorrent(self, args):
        if self.parseduri.name == args:
            self.deleted = True
            self.added.pause()
            try:
                shutil.rmtree(self._args[4] + difflib.get_close_matches(self.parseduri.name, os.listdir('./downloads/'))[0])
            except NotADirectoryError:
                os.remove(self._args[4] + difflib.get_close_matches(self.parseduri.name, os.listdir('./downloads/'))[0])
            time.sleep(3)
            os.remove('resumedata/' + difflib.get_close_matches(self.parseduri.name, os.listdir('./resumedata/'))[0])

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
        self.entry2 = wx.TextCtrl(self.panel, size=(200, 30))
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
        torthread([None, None, None,self.entry.GetValue(), self.entry2.GetValue()])
        magntdialog.Destroy(self)

    def setpath(self, event):
        filepath = wx.DirDialog(None, 'Select Folder', './downloads/', wx.DD_DEFAULT_STYLE)
        filepath.ShowModal()
        self.entry2.SetValue(filepath.GetPath())

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.db =sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS downloads (name, date, link, path)')
        self.panel = wx.Panel(self)
        self.boxsizer = wx.BoxSizer(wx.VERTICAL)
        self.indeex = 0
        self.ult = ULC.UltimateListCtrl(self.panel, agwStyle= ULC.ULC_REPORT | ULC.ULC_VRULES | ULC.ULC_HRULES | ULC.ULC_SINGLE_SEL | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Name"
        self.ult.InsertColumnInfo(0, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Progress"
        self.ult.InsertColumnInfo(1, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Status"
        self.ult.InsertColumnInfo(2, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Seeds"
        self.ult.InsertColumnInfo(3, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Peers"
        self.ult.InsertColumnInfo(4, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Download Speed"
        self.ult.InsertColumnInfo(5, info)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Upload Speed"
        self.ult.InsertColumnInfo(6, info)

        self.ult.SetColumnWidth(0, 250)
        self.ult.SetColumnWidth(1, 100)
        self.ult.SetColumnWidth(2, 150)
        self.ult.SetColumnWidth(3, 50)
        self.ult.SetColumnWidth(4, 50)
        self.ult.SetColumnWidth(5, 120)
        self.ult.SetColumnWidth(6, 120)

        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()

        if self.alldowns != []:
            for i in self.alldowns:
                torthread(i)
                self.ult.InsertStringItem(i[0], i[1])

        self.boxsizer.Add(self.ult, 1, wx.EXPAND)
        self.panel.SetSizer(self.boxsizer)
        pub.subscribe(self.updateprog, 'update')
        pub.subscribe(self.addtor, 'add')
        self.showmenu()
        self.Bind(wx.EVT_MENU, self.magnet, self.frstentry)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRight)
        self.db.close()
    def OnRight(self, event):
        popupmenu = wx.Menu()
        PauseResume = popupmenu.Append(-1, "Pause/Resume")
        Delete = popupmenu.Append(-1, 'Delete With Files')
        self.Bind(wx.EVT_MENU, self.OnPause, PauseResume)
        self.Bind(wx.EVT_MENU, self.OnDelete, Delete)
        self.ult.PopupMenu(popupmenu)

    def OnPause(self, event):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT * FROM downloads')
        self.all = self.cur.fetchall()
        ind = self.ult.GetFirstSelected()
        pub.sendMessage('pausetor', args=self.all[ind][0])
    def OnDelete(self, event):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT * FROM downloads')
        self.all = self.cur.fetchall()
        ind = self.ult.GetFirstSelected()
        self.cur.execute('DELETE FROM downloads WHERE oid =' + str(ind + 1))
        self.ult.DeleteItem(ind)
        self.db.commit()
        self.db.close()
        pub.sendMessage('deletetor', args=self.all[ind][0])

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

    def updateprog(self,message):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        for x,y in enumerate(self.alldowns):
            if y[1] == message[6]:
                self.gawk = wx.Gauge(self.ult)
                self.gawk.SetValue(int(message[0]))
                self.ult.SetItemWindow(self.alldowns[x][0] - 1, 1, self.gawk, expand=True)
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 2, str(message[5]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 3, str(message[1]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 4, str(message[2]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 5, str(round(message[3], 1)) + 'MB')
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 6, str(message[4]) + 'MB')
        self.db.close()
    def addtor(self, args):
        self.db =sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        tmplist = []
        for im in self.alldowns:
            tmplist.append(im[1])
        if args[0] in tmplist:
            print('torrent already in')
        else:
            self.cur.execute('INSERT INTO downloads VALUES (:torname,:tordate,:link, :path)',
            {
                'torname': args[0],
                'tordate': args[1],
                'link': args[2],
                'path': args[3]
            }
            )
            try:
                self.ult.InsertStringItem(self.alldowns[-1][0], args[0])
            except IndexError:
                self.ult.InsertStringItem(0, args[0])

        self.db.commit()
        self.cur.close()
        self.db.close()

class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        self.frame = MyFrame(parent=None, title='pyTorrent', size=(840, 350))
        self.frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()