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

class Status(Gtk.Table):
    regs = [ 'PV', 'dSV', 'OUT', 'Pr+t', 'flags' ]
    def __init__(self, pid):
        Gtk.Table.__init__(self, 5, 3)
        self.labels = {}
        self.refreshed = False
        self.pid = pid
        for row, n in enumerate([ 'PV', 'dSV', 'OUT', 'Pr', 't']):
            label = Gtk.Label(n)
            label.set_alignment(0, 0.5)
            self.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            if n == 'Pr':
                text = 'Step'
            elif n == 't':
                text = 'Step time elapsed'
            else:
                text = pld.registers[n][0]

            label = Gtk.Label(text)
            label.set_alignment(0, 0.5)
            self.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            label = Gtk.Label()
            label.set_alignment(0, 0.5)
            self.attach(label, 2, 3, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
            self.labels[n] = label

        for row, n in enumerate(pld.bits):
            label = Gtk.Label(n)
            label.set_alignment(0, 0.5)
            self.attach(label, 0, 1, row+5, row+6, yoptions=Gtk.AttachOptions.SHRINK)

            label = Gtk.Label(pld.bit_desc[n])
            label.set_alignment(0, 0.5)
            self.attach(label, 1, 2, row+5, row+6, yoptions=Gtk.AttachOptions.SHRINK)

            label = Gtk.Label()
            label.set_alignment(0, 0.5)
            self.attach(label, 2, 3, row+5, row+6, yoptions=Gtk.AttachOptions.SHRINK)
            self.labels[n] = label

        pid.connect('changed', self.changed)

    def changed(self, pid, n, val, mult):
        if n not in self.regs:
            return
        if n == 'Pr+t':
            self.labels['Pr'].set_text(str(val[0]))
            self.labels['t'].set_text(str(val[1]))
        elif n == 'flags':
            for key, item in val.iteritems():
                self.labels[key].set_text(str(item))
        else:
            if mult == 0.1:
                self.labels[n].set_text('%.1f' % val)
            else:
                self.labels[n].set_text('%d' % val)

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
        for n in self.regs:
            if n == 'flags':
                d = self.pid.flags()
            else:
                d = self.pid.holding_read(n)
            d.addErrback(lambda x: None)
        yield self.pid.process_queue()

