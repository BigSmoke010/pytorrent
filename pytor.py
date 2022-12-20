import wx
import libtorrent as lt
import time
import threading
from pubsub import pub
from wx.lib.agw import ultimatelistctrl as ULC

class torthread(threading.Thread):
    def __init__(self, args):
        super().__init__(args=args)
        self.start()
    def run(self):
        added = s.add_torrent(lt.parse_magnet_uri(self._args))
        while not added.has_metadata:
            time.sleep(1)
            print('got metada')
        while added.status().state != lt.torrent_status.seeding:
            se = added.status()
            progress = se.progress * 100

            time.sleep(2)
            pub.sendMessage('update', message=[progress])


    def AfterRun(self):
        dlg=wx.MessageDialog(None, 'Done', "Called after", wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


class magntdialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.InitUi()
    def InitUi(self):
        self.panel = wx.Panel(self)
        boxsizr = wx.BoxSizer(wx.VERTICAL)
        stbx = wx.StaticBox(self.panel,-1,'Submit Magnet Link')
        sttcbx = wx.StaticBoxSizer(stbx, wx.VERTICAL)
        self.entry = wx.TextCtrl(self.panel,size=(200,30))
        sttcbx.Add(self.entry, 0, wx.ALIGN_CENTER)
        sttcbx.Add(wx.Button(self.panel, -1, 'Submit'), 0, wx.ALIGN_CENTER)
        boxsizr.Add(sttcbx, 0, wx.ALIGN_CENTER)
        self.panel.SetSizer(boxsizr)
        self.panel.Bind(wx.EVT_BUTTON, self.getmagnet)

    def getmagnet(self, event):
        torthread(self.entry.GetValue())
        magntdialog.Destroy(self)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.panel = wx.Panel(self)
        self.boxsizer = wx.BoxSizer(wx.VERTICAL)
        self.ult = ULC.UltimateListCtrl(self.panel, agwStyle=wx.LC_REPORT)

        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Name"
        self.ult.InsertColumnInfo(0, info)
        info = ULC.UltimateListItem()
        info._mask = wx.LIST_MASK_TEXT
        info._text = "Progress"
        self.ult.InsertColumnInfo(1, info)
        ultitem = ULC.UltimateListItem()
        ultitem._
        self.ult.SetColumnWidth(0, 150)
        self.ult.SetColumnWidth(1, 150)
        self.boxsizer.Add(self.ult, 1, wx.EXPAND)
        self.panel.SetSizer(self.boxsizer)
        pub.subscribe(self.updateprog, 'update')
        self.showmenu()
        self.Bind(wx.EVT_MENU, self.magnet, self.frstentry)
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
        self.gaug.SetValue(int(message[0]))
        self.text.SetLabelText(message)
        print(message)

class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        self.frame = MyFrame(parent=None, title='pyTorrent')
        self.frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()