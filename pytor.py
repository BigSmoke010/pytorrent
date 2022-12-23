import wx
import libtorrent as lt
import time
import datetime
import threading
from pubsub import pub
from wx.lib.agw import ultimatelistctrl as ULC
import sqlite3
import os

class torthread(threading.Thread):
    def __init__(self, args):
        super().__init__(args=args)
        self.start()

    def run(self):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.curs = self.db.cursor()
        self.curs.execute('SELECT * FROM downloads')
        self.alls = self.curs.fetchall()
        self.db.close()
        parseduri = lt.parse_magnet_uri(self._args[3])
        parseduri.save_path = './downloads/'
        tmplist = []
        for im in self.alls:
            tmplist.append(im[0])
        if parseduri.name in tmplist:
            with open('resumedata/' + parseduri.name, 'rb') as r:
                print('reading')
                resumedata = lt.read_resume_data(r.read())
                resumedata.save_path = './downloads/'
                self.added = s.add_torrent(resumedata)
        if parseduri.name not in tmplist:
            print('not reading')
            parseduri.save_path = './downloads/'
            self.added = s.add_torrent(parseduri)
        pub.sendMessage('add', args=[parseduri.name, datetime.datetime.now(), self._args[3], lt.write_resume_data(lt.parse_magnet_uri(self._args[3])), self.added.status().save_path])
        while self.added.status().state != lt.torrent_status.seeding:
            x = lt.write_resume_data_buf(lt.parse_magnet_uri(self._args[3]))
            try:
                os.remove('among')
            except FileNotFoundError:
                pass
            with open ('resumedata/' + parseduri.name, 'wb') as f:
                f.write(x)
            self.db = sqlite3.connect('downloads.db', check_same_thread=False)
            self.curs = self.db.cursor()
            self.curs.execute('SELECT * FROM downloads')
            self.alls = self.curs.fetchall()
            for im in self.alls:
                if parseduri.name not in tmplist:
                    tmplist.append(im[0])
            print(tmplist)
            print(parseduri.name)
            if parseduri.name not in tmplist:
                print('bb')
                self.added.stop()
                break
            se = self.added.status()
            progress = se.progress * 100
            time.sleep(3)
            pub.sendMessage('update', message=[progress,se.num_seeds,se.num_peers, se.download_rate / 1000000, lt.write_resume_data(lt.parse_magnet_uri(self._args[3])), se.upload_rate / 1000000, se.state,parseduri.name])
        while self.added.status().state == lt.torrent_status.seeding:
            x = lt.write_resume_data_buf(lt.parse_magnet_uri(self._args[3]))
            try:
                os.remove('among')
            except FileNotFoundError:
                pass
            with open ('among', 'wb') as f:
                f.write(x)
            self.db = sqlite3.connect('downloads.db', check_same_thread=False)
            self.curs = self.db.cursor()
            self.curs.execute('SELECT * FROM downloads')
            self.alls = self.curs.fetchall()
            for im in self.alls:
                if parseduri.name not in tmplist:
                    tmplist.append(im[0])
            print(tmplist)
            print(parseduri.name)
            if parseduri.name not in tmplist:
                print('bb')
                self.added.stop()
                break
            se = self.added.status()
            progress = se.progress * 100
            time.sleep(3)
            pub.sendMessage('update', message=[progress,se.num_seeds,se.num_peers, se.download_rate / 1000000, lt.write_resume_data(lt.parse_magnet_uri(self._args[3])), se.upload_rate / 1000000, se.state,parseduri.name])


class magntdialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.InitUi()
    def InitUi(self):
        self.panel = wx.Panel(self)
        boxsizr = wx.BoxSizer(wx.VERTICAL)
        stbx = wx.StaticBox(self.panel,-1,'Submit Magnet Link')
        sttcbx = wx.StaticBoxSizer(stbx, wx.VERTICAL)
        self.entry = wx.TextCtrl(self.panel,size=(250,30))
        sttcbx.Add(self.entry, 0, wx.ALIGN_CENTER)
        sttcbx.Add(wx.Button(self.panel, -1, 'Submit'), 0, wx.ALIGN_CENTER)
        boxsizr.Add(sttcbx, 0, wx.ALIGN_CENTER)
        self.panel.SetSizer(boxsizr)
        self.panel.Bind(wx.EVT_BUTTON, self.getmagnet)

    def getmagnet(self, event):
        torthread([None, None, None,self.entry.GetValue()])
        magntdialog.Destroy(self)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.db =sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS downloads (name, date, link)')
        self.panel = wx.Panel(self)
        self.boxsizer = wx.BoxSizer(wx.VERTICAL)
        self.indeex = 0
        self.ult = ULC.UltimateListCtrl(self.panel, agwStyle=wx.LC_REPORT)
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
        print(len(self.alldowns))

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

    def OnRight(self, event: wx.Event):
        # show Right-Click-Menu
        popupmenu = wx.Menu()
        Pause = popupmenu.Append(-1, "Pause")
        Delete = popupmenu.Append(-1, 'Delete')
        self.Bind(wx.EVT_MENU, self.OnPause, Pause)
        self.Bind(wx.EVT_MENU, self.OnDelete, Delete)
        self.ult.PopupMenu(popupmenu)

    def OnPause(self, event):
        print(self.ult.GetFirstSelected())

    def OnDelete(self, event):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        ind = self.ult.GetFirstSelected()
        self.cur.execute('DELETE FROM downloads WHERE oid =' + str(ind +  1))
        self.ult.DeleteItem(ind)
        self.db.commit()
        self.db.close()

    def showmenu(self):
        self.frstmenu = wx.Menu()
        self.frstentry = self.frstmenu.Append(0, item='Add Magnet')
        self.scndentry = self.frstmenu.Append(1, item='Open .torrent')
        self.mainmenu = wx.MenuBar()
        self.mainmenu.Append(self.frstmenu, 'Open')
        self.SetMenuBar(self.mainmenu)
    def magnet(self, event):
        dilaog = magntdialog(None, title='show', size=(210,130))
        dilaog.ShowModal()
        dilaog.Destroy()
    def updateprog(self,message):
        self.db = sqlite3.connect('downloads.db', check_same_thread=False)
        self.cur = self.db.cursor()
        self.cur.execute('SELECT oid,* FROM downloads')
        self.alldowns = self.cur.fetchall()
        for x,y in enumerate(self.alldowns):
            if y[1] == message[7]:
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 1, str(round(message[0], 1)) + '%')
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 2, str(message[6]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 3, str(message[1]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 4, str(message[2]))
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 5, str(round(message[3], 1)) + 'MB')
                self.ult.SetStringItem(self.alldowns[x][0] - 1, 6, str(message[5]) + 'MB')


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
            self.cur.execute('INSERT INTO downloads VALUES (:torname,:tordate,:link)',
            {
                'torname': args[0],
                'tordate': args[1],
                'link': args[2]
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
        self.frame = MyFrame(parent=None, title='pyTorrent', size=(800, 350))
        self.frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()