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
        self.curs.close()
        self.db.close()
        self.parseduri = lt.parse_magnet_uri(self._args[3])
        self.parseduri.save_path = self._args[4]
        self.parseduri.save_path = self._args[4]
        self.added = s.add_torrent(self.parseduri)
        pub.sendMessage('add', args=[self.parseduri.name, datetime.datetime.now(), self._args[3], self._args[4], 'no'])
        se = self.added.status()

        while self.added.status() and not self.deleted:
            self.se = self.added.status()
            if self.deleted:
                self.added.pause()
            if self.paused and not self.resumed:
                self.ispaused = 'yes'
                self.added.pause()
            if self.resumed and not self.paused:
                self.ispaused = 'no'
                self.added.resume()
            pub.sendMessage('update', message=[self.se.progress * 100 ,self.se.num_seeds, self.se.num_peers, self.se.download_rate / 1000000, self.se.upload_rate / 1000000, self.se.state,self.parseduri.name, self.se.total / 1000000, self.se.total_done / 1000000, self.ispaused])
            time.sleep(5)


    def deletetorrent(self, args):
        if self.parseduri.name == args:
            print('deeleteeeing')
            self.deleted = True
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
        torthread([None, None, None,self.entry.GetValue(), self.entry2.GetValue()])
        magntdialog.Destroy(self)

    def setpath(self, event):
        filepath = wx.DirDialog(None, 'Select Folder', './downloads/', wx.DD_DEFAULT_STYLE)
        filepath.ShowModal()
        filepath.Destroy()
        self.entry2.SetValue(filepath.GetPath())

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.db =sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
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
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Total Download"
        self.ult.InsertColumnInfo(7, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Total Downloaded"
        self.ult.InsertColumnInfo(8, info)
        self.ult.SetColumnWidth(0, 250)
        self.ult.SetColumnWidth(1, 100)
        self.ult.SetColumnWidth(2, 150)
        self.ult.SetColumnWidth(3, 50)
        self.ult.SetColumnWidth(4, 50)
        self.ult.SetColumnWidth(5, 120)
        self.ult.SetColumnWidth(6, 120)
        self.ult.SetColumnWidth(7, 120)
        self.ult.SetColumnWidth(8, 120)
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.cur.close()
        self.db.close()
        self.allgauges = []
        if self.alldowns != []:
            for i in self.alldowns:
                if i[-1] != 'yes':
                    self.allgauges.append((i[1],wx.Gauge(self.ult)))
                    torthread(i)
                    self.ult.InsertStringItem(i[0], i[1])
                    time.sleep(1)
        self.updategauges()
        self.boxsizer.Add(self.ult, 1, wx.EXPAND)
        self.panel.SetSizer(self.boxsizer)
        pub.subscribe(self.updateprog, 'update')
        pub.subscribe(self.addtor, 'add')
        self.showmenu()
        self.Bind(wx.EVT_MENU, self.magnet, self.frstentry)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRight)
    def updategauges(self):
        for x, gaug in enumerate(self.allgauges):
            try:
                self.ult.SetItemWindow(x, 1,  gaug[1], expand=True)
            except AttributeError:
                pass
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
        self.cur.close()
        self.db.close()
    def OnDelete(self, event):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT * FROM downloads')
        self.all = self.cur.fetchall()
        ind = self.ult.GetFirstSelected()
        self.cur.execute('DELETE FROM downloads WHERE oid =' + str(ind + 1))
        self.ult.DeleteItem(ind)
        print(self.allgauges)
        del self.allgauges[ind]
        print(self.allgauges)
        self.db.commit()
        self.cur.close()
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
        try :
            lock.acquire(True)
            for x,y in enumerate(self.alldowns):
                if y[1] == message[6]:
                    for name,gaug in self.allgauges:
                        if name == message[6]:
                            gaug.SetValue(int(message[0]))
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 2, str(message[5]))
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 3, str(message[1]))
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 4, str(message[2]))
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 5, str(round(message[3], 1)) + 'MB')
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 6, str(message[4]) + 'MB')
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 7, str(round(message[7], 2)) + 'MB')
                    self.ult.SetStringItem(self.alldowns[x][0] - 1, 8, str(round(message[8], 2)) + 'MB')

        finally:
            lock.release()
    def addtor(self,args):
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
            self.cur.execute('INSERT INTO downloads VALUES (:torname,:tordate,:link, :path, :ispaused)',
            {
                'torname': args[0],
                'tordate': args[1],
                'link': args[2],
                'path': args[3],
                'ispaused': args[4]
            }
            )
            try:
                self.ult.InsertStringItem(self.alldowns[-1][0], args[0])
                self.allgauges.append((args[0], wx.Gauge(self.ult)))
                self.updategauges()

            except IndexError:
                self.ult.InsertStringItem(0, args[0])

        self.db.commit()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        self.cur.close()
        self.db.close()

class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        self.frame = MyFrame(parent=None, title='pyTorrent', size=(1100, 350))
        self.frame.Show()

s = lt.session()
lock = threading.Lock()
app = MyApp()
app.MainLoop()
