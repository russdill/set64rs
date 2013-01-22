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
import widgets

from gi.repository import Gtk


class PIDTab(Gtk.Table):
    def __init__(self, pid):
        Gtk.Table.__init__(self, len(self.regs), 4)
        for row, n in enumerate(self.regs):
            reg = pld.registers[n]

            label = Gtk.Label(n)
            label.set_alignment(0, 0.5)
            self.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            label = Gtk.Label(reg[0])
            label.set_alignment(0, 0.5)
            self.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

            if type(reg[2]) is list:
                combo = widgets.PIDComboBoxText(pid, n)
                self.attach(combo, 3, 4, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
            elif type(reg[2]) is dict:
                combo = widgets.PIDSpinCombo(pid, n)
                self.attach(combo.spin, 3, 4, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
                self.attach(combo, 2, 3, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
            else:
                spin = widgets.PIDSpinButton(pid, n)
                self.attach(spin, 3, 4, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)

    def on_show(self):
        pass

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

