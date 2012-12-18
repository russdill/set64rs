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

from gi.repository import Gtk
import twisted.internet.defer
import pld

class Ramp_soak(Gtk.ScrolledWindow):
    def __init__(self, pid):
        self.pid = pid
        self.refreshed = False
        self.store = Gtk.ListStore(int, int, str, int, int)
        self.tree = Gtk.TreeView(self.store)
        Gtk.ScrolledWindow.__init__(self)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Step", renderer, text=0)
        self.tree.append_column(column)

        reg = pld.registers['C-01']
        adj = Gtk.Adjustment(reg[3]+1, reg[2][0]+1, reg[2][1]+1, reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.connect('edited', self.on_group_edited)
        column = Gtk.TreeViewColumn("PID Group", renderer, text=1)
        self.tree.append_column(column)

        mode_store = Gtk.ListStore(str)
        for mode in pld.run_modes.keys():
            mode_store.append([mode])

        renderer = Gtk.CellRendererCombo()
        renderer.set_property("editable", True)
        renderer.set_property("model", mode_store)
        renderer.set_property("has-entry", False)
        renderer.set_property("text-column", 0)
        renderer.connect('edited', self.on_mode_edited)
        column = Gtk.TreeViewColumn("Mode", renderer, text=2)
        self.tree.append_column(column)

        reg = pld.registers['t-01']
        adj = Gtk.Adjustment(1, reg[2]['Run'][0], reg[2]['Run'][1], reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.connect('edited', self.on_time_edited)
        column = Gtk.TreeViewColumn("Runtime/Jump to", renderer, text=3)
        self.tree.append_column(column)

        reg = pld.registers['Sv01']
        adj = Gtk.Adjustment(reg[3], reg[2][0], reg[2][1], reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.connect('edited', self.on_sv_edited)
        column = Gtk.TreeViewColumn("Set Value", renderer, text=4)
        self.tree.append_column(column)

        for i in range(1,65):
            self.store.append([i, 1, 'Pause', 1, 0])

        self.add(self.tree)
        pid.connect('changed', self.changed)

    def on_group_edited(self, widget, path, text):
        n = 'C-%02d' % (int(str(path)) + 1)
        d = self.pid.raw(n, int(text)-1)
        d.addErrback(lambda x: None)

    def on_mode_edited(self, widget, path, text):
        n = 't-%02d' % (int(str(path)) + 1)
        if text == 'Jump' or text == 'Run':
            treeiter = self.store.get_iter(path)
            idx = self.store.get(treeiter, 3)[0]
            if text == 'Jump':
                if not 1 <= idx <= 64:
                    idx = 1
                idx = -idx
            text = (text, idx)
        d = self.pid.raw(n, text)
        d.addErrback(lambda x: None)

    def on_time_edited(self, widget, path, text):
        n = 't-%02d' % (int(str(path)) + 1)
        treeiter = self.store.get_iter(path)
        mode = self.store.get(treeiter, 2)[0]
        val = int(text)
        if mode == 'Jump':
            if not 1 <= val <= 64:
                return
            val = -val
        elif mode == 'Run':
            pass
        else:
            return
        d = self.pid.raw(n, (mode, val))
        d.addErrback(lambda x: None)

    def on_sv_edited(self, widget, path, text):
        n = 'Sv%02d' % (int(str(path)) + 1)
        d = self.pid.raw(n, int(text))
        d.addErrback(lambda x: None)

    def changed(self, pid, n, val, mult):
        if len(n) != 4:
            return
        if n[0] in "Ct":
            if n[1] != '-':
                return
        elif n[0:2] == 'Sv':
            pass
        else:
            return
        if n[2] not in "0123456789" or n[3] not in "0123456789":
            return

        print 'changed', n, val
        path = str(int(n[2:4]) - 1)
        self.tree.set_cursor(path, None)
        treeiter = self.store.get_iter(path)
        if n[0] == 'C':
            val = 0 if val is None else val
            self.store.set(treeiter, 1, val+1)
        elif n[0] == 't':
            idx = None
            if type(val) is tuple:
                val, idx = val
            if val == 'Run':
                self.store.set(treeiter, 3, idx)
            elif val == 'Jump':
                self.store.set(treeiter, 3, abs(idx))
            self.store.set(treeiter, 2, val)
        else:
            val = 0 if val is None else val
            self.store.set(treeiter, 4, int(val))

    def on_show(self):
        if not self.refreshed:
            self.refreshed = True
            try:
                self.refresh()
            except:
                self.refreshed = False

    def refresh(self):
        d = self._refresh()
        d.addErrback(lambda x: None)

    @twisted.internet.defer.inlineCallbacks
    def _refresh(self):
        self.tree.set_cursor("0", None)
        for row in range(1,65):
            for col in [ "C-", "t-", "Sv" ]:
                d = self.pid.holding_read(col + ('%02d' % row))
                d.addErrback(lambda x: None)
        yield self.pid.process_queue()
        self.tree.set_cursor("0", None)
        self.refreshed = True

