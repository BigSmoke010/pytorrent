import wx
import libtorrent as lt
import time
import threading
from pubsub import pub

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
            x = se.progress * 100
            time.sleep(2)
            pub.sendMessage('update', message=x)


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
        self.entry = wx.TextCtrl(self.panel,size=(200,30))
        boxsizr.Add(wx.StaticText(self.panel, -1, 'please enter magnet'), 0, wx.ALIGN_CENTER)
        boxsizr.Add(self.entry, 0, wx.ALIGN_CENTER)
        boxsizr.Add(wx.Button(self.panel, -1, 'Submit'), 0, wx.ALIGN_CENTER)
        self.panel.SetSizerAndFit(boxsizr)
        self.panel.Bind(wx.EVT_BUTTON, self.getmagnet)
    def getmagnet(self, event):
        torthread(self.entry.GetValue())
        magntdialog.Destroy(self)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.x = 0
        self.panel = wx.Panel(self)
        self.boxsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.text = wx.StaticText(self.panel,-1,'Progress :' + str(self.x))
        self.gaug = wx.Gauge(self.panel)
        self.boxsizer.Add(self.text)
        self.boxsizer.Add(self.gaug)
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
        dilaog = magntdialog(None, title='show', size=(300,130))
        dilaog.ShowModal()
        dilaog.Destroy()
    def updateprog(self,message,arg2=None):
        self.gaug.SetValue(int(message))
        self.text.SetLabelText(str(message))
        print(message)

class MyApp(wx.App):
    def __init__(self):
        super().__init__()
        self.frame = MyFrame(parent=None, title='pyTorrent')
        self.frame.Show()

s = lt.session()
app = MyApp()
app.MainLoop()