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
import pld
import twisted.internet.defer

class PID(Gtk.TreeView):
    def __init__(self, pid):
        self.pid = pid
        self.refreshed = False
        self.store = Gtk.ListStore(int, str, int, int)
        Gtk.TreeView.__init__(self, self.store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Group", renderer, text=0)
        self.append_column(column)

        reg = pld.registers['P1']
        adj = Gtk.Adjustment(reg[3], reg[2][0], reg[2][1], reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.set_property("digits", 1)
        renderer.connect('edited', self.on_p_edited)
        column = Gtk.TreeViewColumn("P                              ", renderer, text=1)
        self.append_column(column)

        reg = pld.registers['I1']
        adj = Gtk.Adjustment(reg[3], reg[2][0], reg[2][1], reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.set_property("width-chars", 20)
        renderer.connect('edited', self.on_i_edited)
        column = Gtk.TreeViewColumn("I                              ", renderer, text=2)
        self.append_column(column)

        reg = pld.registers['d1']
        adj = Gtk.Adjustment(reg[3], reg[2][0], reg[2][1], reg[4])
        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)
        renderer.set_property("adjustment", adj)
        renderer.connect('edited', self.on_d_edited)
        column = Gtk.TreeViewColumn("d                              ", renderer, text=3)
        self.append_column(column)

        for i in range(1,10):
            self.store.append([i, '0.1', 0, 0])

        self.popup = Gtk.Menu()
        item = Gtk.MenuItem('Load from work tab')
        item.connect('activate', self.on_load)
        self.popup.append(item)
        item = Gtk.MenuItem('Export to work tab')
        item.connect('activate', self.on_export)
        self.popup.append(item)

        pid.connect('changed', self.changed)
        self.connect('button-release-event', self.on_button)

    def on_p_edited(self, widget, path, text):
        n = 'P'+(str(int(path) + 1))
        try:
            d = self.pid.raw(n, float(text))
            d.addErrback(lambda x: None)
        except:
            pass

    def on_i_edited(self, widget, path, text):
        n = 'I'+(str(int(path) + 1))
        try:
            d = self.pid.raw(n, int(text))
            d.addErrback(lambda x: None)
        except:
            pass

    def on_d_edited(self, widget, path, text):
        n = 'd'+(str(int(path) + 1))
        try:
            d = self.pid.raw(n, int(text))
            d.addErrback(lambda x: None)
        except:
            pass

    def on_button(self, widget, event):
        if event.button != 3:
            return

        path_info = self.get_path_at_pos(event.x, event.y)
        if path_info is None:
            return

        self.click_path, col, x, y = path_info
        self.grab_focus()
        self.set_cursor(self.click_path, None)
        self.popup.popup(None, None, None, None, event.button, event.time)
        self.popup.show_all()
        return True

    def on_load(self, widget):
        d = self.do_load(self.click_path)
        d.addErrback(lambda x: None)

    @twisted.internet.defer.inlineCallbacks
    def do_load(self, path):
        row = str(int(str(path)) + 1)
        for i in 'PId':
            val, mult = yield self.pid.holding_read(i)
            yield self.pid.raw(i + row, val)

    def on_export(self, widget):
        d = self.do_export(self.click_path)

    @twisted.internet.defer.inlineCallbacks
    def do_export(self, path):
        row = str(int(str(path)) + 1)
        for i in 'PId':
            val, mult = yield self.pid.holding_read(i + row)
            yield self.pid.raw(i, val)

    def changed(self, pid, n, val, mult):
        if len(n) != 2 or n[0] not in "PId" or n[1] not in "123456789":
            return
        path = str(int(n[1]) - 1)
        treeiter = self.store.get_iter(path)
        col = '_PId'.index(n[0])
        if n[0] == 'P':
            val = '%.1f' % (0.1 if val is None else val)
        else:
            val = 0 if val is None else val
        self.store.set(treeiter, col, val)

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
        for row in range(1,10):
            self.set_cursor(str(row-1), None)
            for col in "PId":
                d = self.pid.holding_read(col + str(row))
                d.addErrback(lambda x: None)
        yield self.pid.process_queue()
        self.set_cursor("0", None)

