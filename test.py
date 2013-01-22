#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2012 Russ Dill <Russ.Dill@asu.edu>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import time

import twisted.internet.gtk3reactor
twisted.internet.gtk3reactor.install()

import pld
import registers_tab
import status_tab
import pid_tab
import ramp_soak_tab
import autotune
import monitor

from gi.repository import Gtk

UI_INFO = """
<ui>
  <menubar name='MenuBar'>
    <menu action='FileMenu'>
      <menuitem action='FileQuit' />
    </menu>
    <menu action='ActionMenu'>
      <menuitem action='ActionAT' />
      <menuitem action='ActionMonitor' />
    </menu>
  </menubar>
</ui>
"""

class PIDWindow(Gtk.Window):
    def __init__(self, pid):
        Gtk.Window.__init__(self, title="Set64rs")

        action_group = Gtk.ActionGroup("profile_actions")
        action_group.add_actions([
            ("FileMenu", None, "File", None, None, None),
            ("FileQuit", Gtk.STOCK_QUIT, "_Quit", "<control>Q", None, Gtk.main_quit),
            ("ActionMenu", None, "Action", None, None, None),
            ("ActionAT", None, "Auto-tune", None, None, self.on_at),
            ("ActionMonitor", None, "Monitor", None, None, self.on_monitor)
        ])

        uimanager = Gtk.UIManager()
        uimanager.add_ui_from_string(UI_INFO)
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        uimanager.insert_action_group(action_group)
        menubar = uimanager.get_widget("/MenuBar")

        self.pid = pid
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(registers_tab.Function(pid), Gtk.Label("Function"))
        self.notebook.append_page(registers_tab.Work(pid), Gtk.Label("Work"))
        self.notebook.append_page(registers_tab.Control(pid), Gtk.Label("Control"))
        self.notebook.append_page(status_tab.Status(pid), Gtk.Label("Status"))
        self.notebook.append_page(pid_tab.PID(pid), Gtk.Label("PID"))
        self.notebook.append_page(ramp_soak_tab.Ramp_soak(pid), Gtk.Label("Ramp/soak"))
        self.notebook.connect('switch-page', self.on_select_page)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(menubar, False, False, 0)
        vbox.add(self.notebook)
        self.add(vbox)

    def on_at(self, widget):
        win = autotune.ATWindow(self.pid)
        win.show_all()

    def on_monitor(self, widget):
        win = monitor.MonitorWindow(self.pid)
        win.show_all()

    def on_select_page(self, notebook, page, page_num):
        page.on_show()

def main():
    port = pld.SerialModbusClient("/dev/ttyUSB0", twisted.internet.reactor, timeout=0.1)
    win = PIDWindow(port.protocol)
    win.connect('delete-event', Gtk.main_quit)

    win.show_all()
    twisted.internet.reactor.run()

if __name__ == '__main__':
    main()

