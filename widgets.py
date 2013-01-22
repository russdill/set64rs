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

from gi.repository import Gtk, GObject
import twisted.internet.defer
import math
import pld

import twisted.internet.gtk3reactor

class ActionCheckButton(Gtk.CheckButton):
    def __init__(self, action, read=None, label=None, use_underline=True):
        super(ActionCheckButton, self).__init__(label=label, use_underline=use_underline)
        self.connect('toggled', self.on_toggled)
        self.busy = 0
        self.sens = True
        self.cached = super(ActionCheckButton, self).get_active()
        self.action = action
        self.read = read
        if self.read is not None:
            self.connect('show', self.on_show)
            self.refreshed = False

    def on_show(self, widget):
        if not self.refreshed:
            self.refresh()

    def refresh(self):
        if not self.busy:
            self.busy += 1
            super(ActionCheckButton, self).set_sensitive(False)
            d = self.read()
            d.addCallbacks(self.on_success, self.on_fail)

    def on_toggled(self, button):
        if not self.busy:
            self.busy += 1
            super(ActionCheckButton, self).set_sensitive(False)
            self.stop_emission('toggled')
            d = self.action(super(ActionCheckButton, self).get_active())
            d.addCallbacks(self.on_success, self.on_fail)

    def get_active(self):
        return self.cached

    def set_active(self, active, user=True):
        if not user:
            self.cached = active
            self.busy += 1
            try:
                super(ActionCheckButton, self).set_active(active)
            finally:
                self.busy -= 1
        elif not self.busy:
            super(ActionCheckButton, self).set_active(active)

    def set_sensitive(self, sens):
        self.sens = sens
        super(ActionCheckButton, self).set_sensitive(sens and not self.busy)

    def get_sensitive(self):
        return self.sens

    def on_success(self, n):
        self.cached = n
        self.refreshed = True
        self.on_fail(None)

    def on_fail(self, x):
        super(ActionCheckButton, self).set_active(self.cached)
        super(ActionCheckButton, self).set_sensitive(self.sens)
        self.emit('toggled')
        self.busy -= 1

class PIDCheckButton(ActionCheckButton):
    def __init__(self, pid, name):
        super(PIDComboBoxText, self).__init__(lambda val: pid.raw(name, val), read=lambda name=name: pid.holding_read(name))
        reg = pld.registers[name]
        for text in reg[2]:
            if text is not None:
                self.append_text(text)
        pid.connect('changed', lambda pid, n, val, mult: self.set_active(self.lookup(val), user=False) if n == name else None)


class ActionComboBoxText(Gtk.ComboBoxText):
    def __init__(self, action, read=None):
        super(ActionComboBoxText, self).__init__()
        self.connect('changed', self.on_changed)
        self.busy = 0
        self.sens = True
        self.cached = super(ActionComboBoxText, self).get_active()
        self.action = action
        self.read = read
        if self.read is not None:
            self.connect('show', self.on_show)
            self.refreshed = False

    def on_show(self, widget):
        if not self.refreshed:
            self.refresh()

    def refresh(self):
        if not self.busy:
            self.busy += 1
            super(ActionComboBoxText, self).set_sensitive(False)
            d = self.read()
            d.addCallbacks(self.on_success, self.on_fail)

    def on_changed(self, widget):
        if not self.busy:
            self.busy += 1
            super(ActionComboBoxText, self).set_sensitive(False)
            self.stop_emission('changed')
            d = self.action(super(ActionComboBoxText, self).get_active_text())
            d.addCallbacks(self.on_success, self.on_fail)

    def get_active(self):
        return self.cached

    def lookup_iter(self, string):
        return next(row.iter for row in self.get_model() if row[0] == string)

    def lookup(self, string):
        return next(n for n, row in enumerate(self.get_model()) if row[0] == string)

    def set_active(self, active, user=True):
        if not user:
            self.cached = active
            self.busy += 1
            try:
                super(ActionComboBoxText, self).set_active(active)
            finally:
                self.busy -= 1
        elif not self.busy:
            super(ActionComboBoxText, self).set_active(active)

    def set_sensitive(self, sens):
        self.sens = sens
        super(ActionComboBoxText, self).set_sensitive(sens and not self.busy)

    def get_sensitive(self):
        return self.sens

    def on_success(self, n):
        n, _ = n
        self.set_active_iter(self.lookup_iter(n))
        self.cached = super(ActionComboBoxText, self).get_active()
        self.on_fail(None)

    def on_fail(self, x):
        super(ActionComboBoxText, self).set_active(self.cached)
        super(ActionComboBoxText, self).set_sensitive(self.sens)
        self.emit('changed')
        self.busy -= 1

class PIDComboBoxText(ActionComboBoxText):
    def __init__(self, pid, name):
        super(PIDComboBoxText, self).__init__(lambda val: pid.raw(name, val), read=lambda name=name: pid.holding_read(name))
        reg = pld.registers[name]
        for text in reg[2]:
            if text is not None:
                self.append_text(text)
        pid.connect('changed', lambda pid, n, val, mult: self.set_active(self.lookup(val), user=False) if n == name else None)

class ActionSpinButton(Gtk.SpinButton):
    def __init__(self, action, read=None, adjustment=None, climb_rate=0.0, digits=0):
        super(ActionSpinButton, self).__init__(adjustment=adjustment, climb_rate=climb_rate, digits=digits)
        self.connect('value-changed', self.on_value_changed)
        self.busy = 0
        self.sens = True
        self.cached = super(ActionSpinButton, self).get_value()
        self.action = action
        self.read = read
        if self.read is not None:
            self.connect('show', self.on_show)
            self.refreshed = False

    def on_show(self, widget):
        if not self.refreshed:
            self.refresh()

    def refresh(self):
        if not self.busy:
            self.busy += 1
            super(ActionSpinButton, self).set_sensitive(False)
            d = self.read()
            d.addCallbacks(self.on_success, self.on_fail)

    def on_value_changed(self, button):
        if not self.busy:
            self.busy += 1
            super(ActionSpinButton, self).set_sensitive(False)
            self.stop_emission('value-changed')
            d = self.action(super(ActionSpinButton, self).get_value())
            d.addCallbacks(self.on_success, self.on_fail)

    def get_value(self):
        return self.cached

    def set_value(self, value, user=True, mult=None):
        if not user:
            self.cached = value
            self.busy += 1
            try:
                super(ActionSpinButton, self).set_value(value)
            finally:
                self.busy -= 1
        elif not self.busy:
            super(ActionSpinButton, self).set_value(value)
        if mult is not None:
            self.apply_mult(mult)

    def set_sensitive(self, sens):
        self.sens = sens
        super(ActionSpinButton, self).set_sensitive(sens and not self.busy)

    def get_sensitive(self):
        return self.sens

    def apply_mult(self, mult):
        _, page = self.get_increments()
        self.set_increments(mult, page)
        if mult < 1.0:
            self.set_digits(-math.log10(mult))
        else:
            self.set_digits(0)

    def on_success(self, val):
        val, mult = val
        self.cached = val
        self.apply_mult(mult)
        self.on_fail(None)

    def on_fail(self, x):
        super(ActionSpinButton, self).set_value(self.cached)
        super(ActionSpinButton, self).set_sensitive(self.sens)
        self.emit('value-changed')
        self.busy -= 1

class PIDSpinButton(ActionSpinButton):
    def __init__(self, pid, name):
        super(PIDSpinButton, self).__init__(lambda val: pid.raw(name, val), read=lambda name=name: pid.holding_read(name))
        reg = pld.registers[name]
        adjustment = Gtk.Adjustment()
        adjustment.set_lower(reg[2][0])
        adjustment.set_upper(reg[2][1])
        adjustment.set_step_increment(1)
        self.set_adjustment(adjustment)
        pid.connect('changed', lambda pid, n, val, mult: self.set_value(val, mult=mult, user=False) if n == name else None)

class PIDSpinCombo(Gtk.ComboBoxText):
    def __init__(self, pid, name):
        super(PIDSpinCombo, self).__init__()
        self.reg = pld.registers[name]
        self.spin = Gtk.SpinButton()
        self.spin.connect('value-changed', self.on_value_changed)
        self.connect('changed', self.on_changed)
        for text in self.reg[2]:
            if text is not None:
                self.append_text(text)
        self.busy = 0
        self.sens = True
        self.cached = super(PIDSpinCombo, self).get_active()
        self.adjustment_cached = self.spin.get_adjustment()
        self.spin_cached = self.spin.get_value()
        self.action = lambda val: pid.raw(name, val)
        self.read = lambda name=name: pid.holding_read(name)
        pid.connect('changed', lambda pid, n, val, mult: self.pid_changed(val, mult) if n == name else None)
        if self.read is not None:
            self.connect('show', self.on_show)
            self.refreshed = False

    def on_show(self, widget):
        if not self.refreshed:
            self.refresh()

    def set_adjustment(self, adj):
        self.spin.set_adjustment(adj)

    def get_adjustment(self):
        return self.spin.get_adjustment()

    def refresh(self):
        if not self.busy:
            self.busy += 1
            super(PIDSpinCombo, self).set_sensitive(False)
            self.spin.set_sensitive(False)
            d = self.read()
            d.addCallbacks(self.on_success, self.on_fail)

    def pid_changed(self, curr, mult):
        if type(curr) is tuple:
            curr, val = curr
            self.set_value(val, user=False)
        curr = self.lookup(curr)
        self.set_active(curr, user=False)

    def on_value_changed(self, button):
        if not self.busy:
            self.busy += 1
            super(PIDSpinCombo, self).set_sensitive(False)
            self.spin.set_sensitive(False)
            self.spin.stop_emission('value-changed')
            curr = (self.get_active_text(), self.spin.get_value())
            d = self.action(curr)
            d.addCallbacks(self.on_success, self.on_fail)

    def on_changed(self, button):
        if not self.busy:
            self.busy += 1
            super(PIDSpinCombo, self).set_sensitive(False)
            self.spin.set_sensitive(False)
            self.stop_emission('changed')
            curr = self.get_active_text()
            r = self.reg[2][curr]
            if type(r) is tuple:
                val = min(max(self.spin.get_value(), r[0]), r[1])
                self.adjustment_cached = self.spin.get_adjustment()
                self.spin.get_adjustment().set_lower(r[0])
                self.spin.get_adjustment().set_upper(r[1])
                self.spin.set_digits(0)
                self.spin.get_adjustment().set_step_increment(1)
                self.spin.set_value(val)
                curr = (curr, val)
            d = self.action(curr)
            d.addCallbacks(self.on_success, self.on_fail)

    def get_active(self):
        return self.cached

    def lookup_iter(self, string):
        return next(row.iter for row in self.get_model() if row[0] == string)

    def lookup(self, string):
        return next(n for n, row in enumerate(self.get_model()) if row[0] == string)

    def set_active(self, active, user=True):
        if not user:
            self.cached = active
            self.busy += 1
            try:
                super(PIDSpinCombo, self).set_active(active)
                r = self.reg[2][self.get_active_text()]
                if type(r) is tuple:
                    val = min(max(self.spin.get_value(), r[0]), r[1])
                    self.spin.get_adjustment().set_lower(r[0])
                    self.spin.get_adjustment().set_upper(r[1])
                    self.spin.set_digits(0)
                    self.spin.get_adjustment().set_step_increment(1)
                    self.adjustment_cached = self.spin.get_adjustment()
                    self.spin.set_value(val)
            finally:
                self.busy -= 1
        elif not self.busy:
            super(ActionComboBoxText, self).set_active(active)

    def get_value(self):
        return self.spin_cached

    def set_value(self, value, user=True, mult=None):
        if not user:
            self.spin_cached = value
            self.busy += 1
            try:
                self.spin.set_value(value)
                if mult is not None:
                    self.apply_mult(mult)
            finally:
                self.busy -= 1
        elif not self.busy:
            self.spin.set_value(value)
            if mult is not None:
                self.apply_mult(mult)

    def set_sensitive(self, sens):
        self.sens = sens
        super(PIDSpinCombo, self).set_sensitive(sens and not self.busy)
        r = self.reg[2][self.get_active_text()]
        self.spin.set_sensitive(self.sens and not self.busy and type(r) is tuple)

    def get_sensitive(self):
        return self.sens

    def apply_mult(self, mult):
        _, page = self.spin.get_increments()
        self.spin.set_increments(mult, page)
        if mult < 1.0:
            self.spin.set_digits(-math.log10(mult))
        else:
            self.spin.set_digits(0)

    def on_success(self, val):
        try:
            curr, mult = val
            if type(curr) is tuple:
                curr, val = curr
                self.spin_cached = val
                self.apply_mult(mult)
                self.adjustment_cached = self.spin.get_adjustment()
            self.set_active_iter(self.lookup_iter(curr))
            self.cached = super(PIDSpinCombo, self).get_active()
        finally:
            self.on_fail(None)

    def on_fail(self, x):
        try:
            super(PIDSpinCombo, self).set_active(self.cached)
            self.spin.set_value(self.spin_cached)
            super(PIDSpinCombo, self).set_sensitive(self.sens)
            self.spin.set_adjustment(self.adjustment_cached)
            r = self.reg[2][self.get_active_text()]
            self.spin.set_sensitive(self.sens and type(r) is tuple)
            self.spin.emit('value-changed')
            self.emit('changed')
        finally:
            self.busy -= 1

@twisted.internet.defer.inlineCallbacks
def action(value):
    d = twisted.internet.defer.Deferred()
    twisted.internet.reactor.callLater(1, d.callback, None)
    yield d
    twisted.internet.defer.returnValue(value)

def main():
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    box = Gtk.Box()

    w = ActionCheckButton(action, 'button')
    box.pack_start(w, False, False, 0)

    w = ActionComboBoxText(action)
    w.append_text('foo')
    w.append_text('bar')
    box.pack_start(w, False, False, 0)

    win.add(box)
    win.show_all()
    d = twisted.internet.defer.Deferred()
    def test(foo):
        w.set_active(True, False)
    twisted.internet.reactor.callLater(1, test, None)
    twisted.internet.reactor.run()


if __name__ == '__main__':
    twisted.internet.gtk3reactor.install()
    main()

