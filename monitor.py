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
import time
import twisted.internet.defer
import math

import matplotlib.figure
import matplotlib.ticker
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

class MonitorWindow(Gtk.Window):
    def __init__(self, pid):
        Gtk.Window.__init__(self, title="Monitor")
        self.pid = pid
        pid.connect('changed', self.changed)
        self.from_pid = False
        self.restart = False
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        f = matplotlib.figure.Figure()
        self.axes = f.add_subplot(111)
        self.axes.set_xlabel('Time (sec.)')
        self.axes.set_ylabel('Temperature (C)')
        self.axes.autoscale()
        self.out_axes = self.axes.twinx()
        self.out_axes.set_ylabel('OUT (%)')
        self.out_axes.autoscale()
        self.axes.grid()
        self.pv_x = []
        self.pv_y = []
        self.sv_x = []
        self.sv_y = []
        self.out_x = []
        self.out_y = []
        self.pv_plot, = self.axes.plot(self.pv_x, self.pv_y, 'b--') #b
        self.sv_plot, = self.axes.plot(self.sv_x, self.sv_y, 'k-') #k
        self.out_plot, = self.out_axes.plot(self.out_x, self.out_y, 'r:') #r
        self.out_active = False
        self.sv_active = False

        self.canvas = FigureCanvas(f)
        self.canvas.set_size_request(800,600)

        vbox.add(self.canvas)

        hbox = Gtk.Box()

        combo = Gtk.ComboBoxText()
        for text in pld.registers['ModL'][2]:
            combo.append_text(text)
        combo.connect('changed', self.mode_changed)
        hbox.pack_start(combo, False, False, 0)
        self.modl_combo = combo
        self.modl_old = None

        pid.connect('process-start', lambda x, r, w=combo: w.set_sensitive(False) if 'ModL' == r else None)
        pid.connect('process-end', lambda x, r, w=combo: w.set_sensitive(True) if 'ModL' == r else None)

        label = Gtk.Label('SV')
        hbox.pack_start(label, False, False, 0)

        # Allow changing SV in manual mode
        # FIXME: disable if not SV?
        reg = pld.registers['SV']
        adjustment = Gtk.Adjustment(reg[3], reg[2][0], reg[2][1], 1)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        adjustment.connect('value-changed', self.sv_changed)
        hbox.pack_start(spin, False, False, 0)
        self.sv_old = 0
        self.sv_adj = adjustment
        self.sv_spin = spin
        spin.set_sensitive(self.sv_active)

        pid.connect('process-start', lambda x, r, w=spin: w.set_sensitive(False) if 'SV' == r else None)
        pid.connect('process-end', lambda x, r, w=spin: w.set_sensitive(self.sv_active) if 'SV' == r else None)

        check = Gtk.CheckButton('Manual')
        self.manual_check = check

        label = Gtk.Label('OUT')
        hbox.pack_start(label, False, False, 0)

        reg = pld.registers['OUT']
        adjustment = Gtk.Adjustment(0.0, reg[2][0], reg[2][1], 0.1)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        adjustment.connect('value-changed', self.out_changed)
        hbox.pack_start(spin, False, False, 0)
        self.out_old = 0
        self.out_adj = adjustment
        self.out_spin = spin
        spin.set_sensitive(self.out_active)

        pid.connect('process-start', lambda x, r, w=spin: w.set_sensitive(False) if 'OUT' == r else None)
        pid.connect('process-end', lambda x, r, w=spin: w.set_sensitive(self.out_active) if 'OUT' == r else None)

        # Start/restart program
        button = Gtk.Button('First Step')
        button.connect('clicked', self.on_restart)
        hbox.pack_start(button, False, False, 0)

        button = Gtk.Button('Continue')
        button.connect('clicked', lambda x: self.pid.coil('next'))
        hbox.pack_start(button, False, False, 0)

        button = Gtk.Button('Pause')
        button.connect('clicked', lambda x: self.pid.coil('pause'))
        hbox.pack_start(button, False, False, 0)

        button = Gtk.Button('Last Step')
        button.connect('clicked', lambda x: self.pid.coil('end'))
        hbox.pack_start(button, False, False, 0)

        vbox.add(hbox)

        # Extra information required
        #   Manual/automatic
        #   Program step
        #   Program status (running/pause)
        #   Time/time remaining in step
        #   PV/SV/dSV display?
        #   AL1/AL2

        self.add(vbox)
        self.run = True
        self.d = self.loop()
        self.d.addErrback(lambda x: None)
        self.connect('delete-event', self.on_delete)

    def changed(self, pid, n, val, mult):
        self.from_pid = True
        try:
            if n == 'SV':
                self.sv_spin.set_sensitive(self.sv_active)
                self.sv_adj.set_step_increment(mult)
                if mult < 1.0:
                    self.sv_spin.set_digits(-math.log10(mult))
                else:
                    self.sv_spin.set_digits(0)
                self.sv_adj.set_value(val)
            elif n == 'OUT':
                self.out_spin.set_sensitive(self.out_active)
                self.out_adj.set_step_increment(mult)
                if mult < 1.0:
                    self.out_spin.set_digits(-math.log10(mult))
                else:
                    self.out_spin.set_digits(0)
                self.out_adj.set_value(val)
            elif n == 'ModL':
                self.sv_active = val == 'SV'
                self.sv_spin.set_sensitive(self.sv_active)
                self.modl_combo.set_active(pld.registers[n][2].index(val))
            elif n == 'flags':
                self.out_active = val['A/M']
                self.out_spin.set_sensitive(self.out_active)
        finally:
            self.from_pid = False

    def mode_changed(self, widget):
        if self.from_pid:
            self.modl_old = widget.get_active()
        else:
            self.modl_combo.set_sensitive(False)
            val = pld.registers['ModL'][2][widget.get_active()]
            d = self.pid.raw('ModL', val)
            d.addErrback(lambda x: widget.set_active(self.modl_old))

    def sv_changed(self, adj):
        if self.from_pid:
            self.sv_old = adj.get_value()
        else:
            self.sv_spin.set_sensitive(False)
            val = adj.get_value()
            d = self.pid.raw('SV', val)
            d.addErrback(lambda x: adj.set_value(self.sv_old))

    def out_changed(self, adj):
        if self.from_pid:
            self.out_old = adj.get_value()
        else:
            self.out_spin.set_sensitive(False)
            val = adj.get_value()
            d = self.pid.raw('OUT', val)
            d.addErrback(lambda x: adj.set_value(self.out_old))

    def on_restart(self, widget):
        self.restart = True

    def on_delete(self, widget, event):
        self.run = False

    @twisted.internet.defer.inlineCallbacks
    def loop(self):
        read_inputs = False
        start = time.time()
        while self.run:
            if self.restart:
                start = time.time()
                self.pv_x = []
                self.pv_y = []
                self.sv_x = []
                self.sv_y = []
                self.out_x = []
                self.out_y = []
                self.axes.relim()
                self.axes.autoscale()
                self.canvas.draw()
                self.restart = False
                yield self.pid.coil('start')
                yield self.pid.coil('auto')
            try:
                if not read_inputs:
                    yield self.pid.holding_read('SV')
                    yield self.pid.holding_read('ModL')
                    read_inputs = True
                    #yield self.pid.coil('manual')


                flags = yield self.pid.flags()
        # Extra information required
        #   Manual/automatic
        #   Program step
        #   Program status (running/pause)
        #   Time/time remaining in step
        #   PV/SV/dSV display?
        #   AL1/AL2

                autotune = flags['AT']
                manual = flags['A/M']
                al1 = flags['AL1']
                al2 = flags['AL2']
                val, mult = yield self.pid.holding_read('Pr+t')
                step, step_t = val
                val, mult = yield self.pid.holding_read('t-' + ('%02d' % step))
                step_total = 0
                # FIXME: Next step = PrL if step == PrH?
                step_next = min(step + 1, 64)
                pause = False
                if type(val) is tuple:
                    val, idx = val
                if val == 'Run':
                    step_total = idx
                elif val == 'Jump':
                    step_next = abs(idx)
                elif val == 'Pause':
                    pause = True

                print 'AT', autotune, 'manual', manual
                print 'al1', al1, 'al2', al2
                print 'step', step, step_t, 'of', step_total
                print 'next', step_next
                print 'pause', pause

                pv, mult = yield self.pid.holding_read('PV')
                now = time.time() - start
                if len(self.pv_y) > 1 and self.pv_y[-2] == self.pv_y[-1] == pv:
                    self.pv_x[-1] = now
                else:
                    self.pv_x.append(now)
                    self.pv_y.append(pv)
                self.pv_plot.set_data(self.pv_x, self.pv_y)
                self.axes.relim()
                self.axes.autoscale()
                self.canvas.draw()

                sv, mult = yield self.pid.holding_read('dSV')
                now = time.time() - start
                if len(self.sv_y) > 1 and self.sv_y[-2] == self.sv_y[-1] == sv:
                    self.sv_x[-1] = now
                else:
                    self.sv_x.append(now)
                    self.sv_y.append(sv)
                self.sv_plot.set_data(self.sv_x, self.sv_y)
                self.axes.relim()
                self.axes.autoscale()
                self.canvas.draw()

                out, mult = yield self.pid.holding_read('OUT', busy=False)
                now = time.time() - start
                if len(self.out_y) > 1 and self.out_y[-2] == self.out_y[-1] == out:
                    self.out_x[-1] = now
                else:
                    self.out_x.append(now)
                    self.out_y.append(out)
                self.out_plot.set_data(self.out_x, self.out_y)
                self.out_axes.relim()
                self.out_axes.autoscale()
                self.canvas.draw()
            except Exception, e:
                print 'monitor error', str(e)

            d = twisted.internet.defer.Deferred()
            twisted.internet.reactor.callLater(0.300 , d.callback, None)
            yield d


