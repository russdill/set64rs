#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bisect
import csv
import os

from gi.repository import Gtk
from gi.repository import Gio

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas


UI_INFO = """
<ui>
  <menubar name='MenuBar'>
    <menu action='FileMenu'>
      <menuitem action='FileNew' />
      <menuitem action='FileOpen' />
      <separator />
      <menuitem action='FileSave' />
      <menuitem action='FileSaveAs' />
      <separator />
      <menuitem action='FileQuit' />
    </menu>
  </menubar>
</ui>
"""

class Profile(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Profile")
        #f = Figure(figsize=(5,4), dpi=100)
        f = Figure()
        self.axes = f.add_subplot(111)
        self.axes.set_xlabel('Time (sec.)')
        self.axes.set_ylabel('Temperature (C)')
        self.axes.set_xlim(0, 5*60)
        self.axes.set_ylim(20, 300)
        self.axes.grid()
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.format_xaxis))
        self.x = []
        self.y = []
        self.plot, = self.axes.plot(self.x, self.y, 'o-', picker=5)
        self.minutes = False
        self.file_name = None

        self.canvas = FigureCanvas(f)
        self.canvas.set_size_request(800,600)
        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('button_release_event', self.onrelease)
        self.canvas.mpl_connect('pick_event', self.onpick)
        self.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.picking = None

        self.store = Gtk.ListStore(str, str)
        self.tree = Gtk.TreeView(self.store)

        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_time_edited)
        column = Gtk.TreeViewColumn("Time", renderer, text=0)
        self.tree.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_temp_edited)
        column = Gtk.TreeViewColumn("Temperature", renderer, text=1)
        self.tree.append_column(column)

        self.box = Gtk.Box()
        self.box.pack_start(self.canvas, False, False, 0)
        self.box.pack_start(self.tree, True, True, 0)

        action_group = Gtk.ActionGroup("profile_actions")
        action_group.add_actions([
            ("FileMenu", None, "File", None, None, None),
            ("FileNew", Gtk.STOCK_NEW, "_New", "<control>N", None, self.on_file_new),
            ("FileOpen", Gtk.STOCK_OPEN, "_Open", "<control>O", None, self.on_file_open),
            ("FileSave", Gtk.STOCK_SAVE, "_Save", "<control>S", None, self.on_file_save),
            ("FileSaveAs", Gtk.STOCK_SAVE_AS, "Save _As…", "<shift><control>S", None, self.on_file_save_as),
            ("FileQuit", Gtk.STOCK_QUIT, "_Quit", "<control>Q", None, Gtk.main_quit)
        ])

        uimanager = Gtk.UIManager()
        uimanager.add_ui_from_string(UI_INFO)
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        uimanager.insert_action_group(action_group)

        menubar = uimanager.get_widget("/MenuBar")
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.pack_start(menubar, False, False, 0)
        self.vbox.pack_start(self.box, True, True, 0)
        self.statusbar = Gtk.Statusbar()
        self.status_pos = self.statusbar.get_context_id("position")
        self.vbox.pack_start(self.statusbar, False, False, 0)

        self.add(self.vbox)

    def open_file(self, name):
        reader = csv.reader(open(name, 'rb'))
        x, y = zip(*reader)
        x = [ float(i) for i in x]
        y = [ float(i) for i in y]
        self.x, self.y = x, y
        self.file_name = name
        self.set_title('Profile - ' + name)
        self.update_data()
        self.update_scale()
        self.canvas.draw()

    def save_file(self, name):
        writer = csv.writer(open(name, 'wd'))
        writer.writerows(zip(self.x, self.y))
        self.file_name = name
        self.set_title('Profile - ' + name)

    def on_file_new(self, widget):
        self.file_name = None
        self.set_title('Profile')
        self.x = []
        self.y = []
        self.store.clear()
        self.update_data()
        self.update_scale()
        self.canvas.draw()

    def on_file_open(self, widget):
        dialog = Gtk.FileChooserDialog("", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder_uri(Gio.file_new_for_path(os.curdir).get_uri())
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            try:
                self.open_file(dialog.get_filename())
            except:
                pass       
        dialog.destroy()

    def on_file_save(self, widget):
        if self.file_name is None:
            self.on_file_save_as(widget)
        else:
            self.save_file(self.file_name)

    def on_file_save_as(self, widget):
        dialog = Gtk.FileChooserDialog("", self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_SAVE_AS, Gtk.ResponseType.OK))
        dialog.set_current_folder_uri(Gio.file_new_for_path(os.curdir).get_uri())
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.save_file(dialog.get_filename())
        dialog.destroy()

    def format_xaxis(self, x, pos):
        return self.format_x(x)

    def format_x(self, val):
        m, s = 0, val
        if self.minutes:
            m = int(val / 60)
            s = val % 60
        if m:
            return '%dm%.1fs'%(m,s)
        else:
            return '%.1fs'%s

    def format_y(self, val):
        return '%.1f°C'%val

    def on_time_edited(self, widget, path, text):
        treeiter = self.store.get_iter(path)
        try:
            m, s = "0", "0"
            if 'm' in text:
                m, text = text.split('m')
            if 's' in text:
                s, text = text.split('s')
            else:
                text = ""
            assert len(text) == 0
            val = int(m) * 60.0 + round(float(s), 1)
        except:
            return

        at = max(0, int(path))
        if at != 0:
            val = max(val, self.x[at-1])
        if at != len(self.x)-1:
            val = min(val, self.x[at+1])
        self.store.set(treeiter, 0, self.format_x(val))
        self.x[int(path)] = val
        self.update_data()
        self.update_scale()
        self.canvas.draw()

    def on_temp_edited(self, widget, path, text):
        treeiter = self.store.get_iter(path)
        try:
            if '°' in text:
                text, _ = text.split('°')
            if 'c' in text.lower():
                text, _ = text.lower().split('c')
            val = round(float(text), 1)
        except:
            return
        val = min(300.0, val)
        val = max(20.0, val)
        self.store.set(treeiter, 1, self.format_y(val))
        self.y[int(path)] = val
        self.update_data()
        self.canvas.draw()

    def update_data(self):
        self.plot.set_data(self.x, self.y)

    def update_scale(self):
        if len(self.x) and self.x[-1] + 30 > 5 * 60:
            minutes = int((self.x[-1] + 90) / 60)
        else:
            minutes = 5
        self.axes.set_xlim(0, minutes*60)

    def onclick(self, event):
        if self.picking is not None or event.button != 1:
            return
        xdata = round(event.xdata, 1)
        ydata = round(event.ydata, 1)
        at = bisect.bisect(self.x, xdata)
        self.x.insert(at, xdata)
        self.y.insert(at, ydata)
        self.store.insert(at, [self.format_x(xdata), self.format_y(ydata)])
        self.update_data()
        self.update_scale()
        self.canvas.draw()

    def onrelease(self, event):
        if self.picking is None:
            return
        self.update_scale()
        self.canvas.draw()
        self.picking = None

    def onpick(self, event):
        on = event.artist
        ind = event.ind[0]
        if event.mouseevent.button == 1:
            self.picking = ind
        elif event.mouseevent.button == 3:
            self.x.pop(ind)
            self.y.pop(ind)
            self.store.remove(self.store.get_iter(Gtk.TreePath(ind)))
            self.update_data()
            self.update_scale()
            self.canvas.draw()

    def onmotion(self, event):
        self.statusbar.remove_all(self.status_pos)
        if event.xdata is None or event.ydata is None:
            return
        self.statusbar.push(self.status_pos,
            self.format_x(event.xdata) + ', ' + self.format_y(event.ydata))
        if self.picking is None:
            return
        xdata = max(0, round(event.xdata, 1))
        ydata = round(event.ydata, 1)
        ydata = min(300.0, ydata)
        ydata = max(20.0, ydata)
        if self.picking != 0:
            xdata = max(xdata, self.x[self.picking-1])
        if self.picking != len(self.x)-1:
            xdata = min(xdata, self.x[self.picking+1])
        self.x[self.picking] = xdata
        self.y[self.picking] = ydata
        treeiter = self.store.get_iter(Gtk.TreePath(self.picking))
        self.store.set(treeiter, 0, self.format_x(xdata), 1, self.format_y(ydata))
        self.update_data()
        self.canvas.draw()

def main():
    win = Profile()
    win.connect('delete-event', Gtk.main_quit)

    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()

