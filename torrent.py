from tkinter import *
from tkinter.ttk import *
import libtorrent as lt
import os
import time

root = Tk()
s = lt.session()
txtvar = StringVar()

submitmagnetentry = Entry(root, width=50)
submitmagnetentry.grid(row=0,column=1)

def getmagnet():
    txtvar.set('amosh')
    paramtrs = lt.parse_magnet_uri(submitmagnetentry.get())
    handle = s.add_torrent(paramtrs)
    while not handle.has_metadata:
        time.sleep(1)
        print('got metadata')
    while handle.status().state != lt.torrent_status.seeding:
        se = handle.status()
        txtvar.set('Progress ' + str(se.progress * 100) + '\n' +'Seeds :' + str(se.num_seeds)+ '\n' + 'peers :' + str(se.num_peers) + '\n' + 'download rate : ' + str(se.download_rate / 1000))
        print('Progress ' + str(se.progress * 100) + '\n' +'Seeds :' + str(se.num_seeds)+ '\n' + 'peers :' + str(se.num_peers) + '\n' + 'download rate : ' + str(se.download_rate / 1000))
        time.sleep(2)

submitmagnet = Button(root, text='magnet', command=getmagnet)
submitmagnet.grid(row=0,column=0)
lbox = Listbox(root, width=25, height=25)
lbox.grid(row=1,column=0)

status = Label(root, textvariable=txtvar)
status.grid(row=1,column=1)
txtvar.set('')
for i in os.listdir('downloads/'):
    lbox.insert('end', i)

root.mainloop()

