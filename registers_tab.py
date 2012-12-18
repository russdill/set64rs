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

import pld
import math
import twisted.internet.defer

from gi.repository import Gtk

class PIDTab(Gtk.Table):
    def __init__(self, pid):
        Gtk.Table.__init__(self, len(self.regs), 4)
        self.spin = {}
        self.adj = {}
        self.adj_old = {}
        self.combo = {}
        self.pid = pid
        self.from_pid = False
        self.ignore_combo = False
        self.refreshed = False
        pid.connect('changed', self.changed)
        for row, n in enumerate(self.regs):
            reg = pld.registers[n]

            label = Gtk.Label(n)
            label.set_alignment(0, 0.5)
            self.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            label = Gtk.Label(reg[0])
            label.set_alignment(0, 0.5)
            self.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            adjustment = Gtk.Adjustment()
            spin = Gtk.SpinButton()
            spin.set_adjustment(adjustment)
            self.attach(spin, 3, 4, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
            self.spin[n] = spin
            self.adj[n] = adjustment
            self.adj_old[n] = 0

            if type(reg[2]) is list or type(reg[2]) is dict:
                combo = Gtk.ComboBoxText()
                for text in reg[2]:
                    if text is not None:
                        combo.append_text(text)
                combo.connect('changed', self.combo_changed, n)
                self.combo[n] = combo
                spin.set_sensitive(False)
                self.attach(combo, 2, 3, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
                w = combo
            else:
                adjustment.set_lower(reg[2][0])
                adjustment.set_upper(reg[2][1])
                adjustment.set_step_increment(1)
                w = spin

            pid.connect('process-start', lambda x, r, n=n, w=w: w.set_sensitive(False) if n == r else None)
            pid.connect('process-end', lambda x, r, n=n, w=w: w.set_sensitive(True) if n == r else None)

            adjustment.connect('value-changed', self.adj_changed, n)

    def changed(self, pid, n, val, mult):
        if n not in self.regs:
            return
        self.from_pid = True
        reg = pld.registers[n]
        if type(reg[2]) is list or type(reg[2]) is dict:
            idx = None
            if type(val) is tuple:
                val, idx = val
            model = self.combo[n].get_model()
            for i, row in enumerate(model):
                if row[0] == val:
                    self.combo[n].set_active(i)
                    break
            if idx is not None:
                self.spin[n].set_value(idx)

        else:
            self.adj[n].set_step_increment(mult)
            if mult < 1.0:
                self.spin[n].set_digits(-math.log10(mult))
            else:
                self.spin[n].set_digits(0)
            self.adj[n].set_value(val)
        self.from_pid = False

    def combo_changed(self, combo, n):
        curr = combo.get_active_text()
        reg = pld.registers[n]
        if self.from_pid:
            if type(reg[2]) is dict:
                r = reg[2][curr]
                if type(r) is tuple:
                    self.adj[n].set_lower(r[0])
                    self.adj[n].set_upper(r[1])
                    self.spin[n].set_digits(0)
                    self.adj[n].set_step_increment(1)
                    self.spin[n].set_sensitive(True)
                else:
                    self.spin[n].set_sensitive(False)
        elif not self.ignore_combo:
            self.ignore_combo = True
            combo.set_active(-1)
            if type(reg[2]) is dict and type(reg[2][curr]) is tuple:
                r = reg[2][curr]
                val = self.adj[n].get_value()
                val = max(val, r[0])
                val = min(val, r[1])
                curr = (curr, val)
            d = self.pid.raw(n, curr)
            d.addErrback(lambda x: None)
        else:
            self.ignore_combo = False

    def adj_changed(self, adj, n):
        if self.from_pid:
            self.adj_old[n] = adj.get_value()
        else:
            val = adj.get_value()
            reg = pld.registers[n]
            if type(reg[2]) is dict:
                curr = self.combo[n].get_active_text()
                if type(reg[2][curr]) is tuple:
                    val = (curr, val)
            d = self.pid.raw(n, val)
            d.addErrback(lambda x: adj.set_value(self.adj_old[n]))

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
            d = self.pid.holding_read(n)
            d.addErrback(lambda x: None)
        yield self.pid.process_queue()

class Function(PIDTab):
    regs = [ 'Inty', 'PvL', 'PvH', 'dot', 'rd', 'obty', 'obL', 'obH', 'oAty',
             'EL', 'SS', 'rES', 'uP', 'ModL', 'PrL', 'PrH', 'corf', 'Id', 'bAud' ]
    def __init__(self, pid):
        PIDTab.__init__(self, pid)

class Work(PIDTab):
    regs = [ 'AL1y', 'AL1C', 'AL2y', 'AL2C', 'P', 'I', 'd', 'Ct', 'SF', 'Pd',
             'bb', 'outL', 'outH', 'nout', 'Psb', 'FILt' ]
    def __init__(self, pid):
        PIDTab.__init__(self, pid)

class Control(PIDTab):
    regs = [ 'SV', 'AL1', 'AL2', 'At' ]
    def __init__(self, pid):
        PIDTab.__init__(self, pid)
        # FIMXE: Add NAT and A/T action

