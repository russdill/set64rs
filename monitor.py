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
import widgets
import sys
import traceback

import matplotlib.figure
import matplotlib.ticker
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

class MonitorWindow(Gtk.Window):
    def __init__(self, pid):
        Gtk.Window.__init__(self, title="Monitor")
        self.pid = pid
        self.restart = False
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

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

        self.canvas = FigureCanvas(f)
        self.canvas.set_size_request(800,600)

        vbox.add(self.canvas)

        hbox = Gtk.Box()

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

        hbox.set_sensitive(False)
        vbox.add(hbox)
        main_hbox.add(vbox)

        # Extra information required
        #   Manual/automatic
        #   Program step
        #   Program status (running/pause)
        #   Time/time remaining in step
        #   PV/SV/dSV display?
        #   AL1/AL2

        self.add(main_hbox)

        table = Gtk.Table()
        row = 0

        combo = widgets.PIDComboBoxText(pid, 'ModL')
        pid.connect('changed', lambda pid, n, val, mult, w=combo: w.set_sensitive(not val['A/M']) if n == 'flags' else None)
        label = Gtk.Label('Mode')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        table.attach(combo, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        row += 1


        # Allow changing SV in manual mode
        # FIXME: disable if not SV?
        spin = widgets.PIDSpinButton(pid, 'SV')
        spin.set_sensitive(False)
        #combo.connect('changed', lambda combo, s=spin, c=combo: s.set_sensitive(c.get_active_text() == 'SV'))
        pid.connect('changed', lambda pid, n, val, mult, w=spin, c=combo: w.set_sensitive(not val['A/M'] and c.get_active_text() == 'SV') if n == 'flags' else None)
        pid.connect('changed', lambda pid, n, val, mult, w=spin: w.set_sensitive(val == 'SV') if n == 'ModL' else None)
        pid.connect('changed', lambda pid, n, val, mult, w=hbox: w.set_sensitive(val != 'SV') if n == 'ModL' else None)

        label = Gtk.Label('Set value')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        table.attach(spin, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        row += 1

        label = Gtk.Label('Dynamic SV')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        pid.connect('changed', lambda pid, n, val, mult, w=label: w.set_text('%0.1f'%val if mult == .1 else '%d'%val) if n == 'dSV' else None)
        row += 1

        label = Gtk.Label('PV')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        pid.connect('changed', lambda pid, n, val, mult, w=label: w.set_text('%0.1f'%val if mult == .1 else '%d'%val) if n == 'PV' else None)
        row += 1

        check = widgets.ActionCheckButton(lambda val: pid.coil('manual' if val else 'auto', val), read=lambda p=pid: p.flag('A/M'))
        pid.connect('changed', lambda pid, n, val, mult, w=check: w.set_active(val['A/M'], user=False) if n == 'flags' else None)
        label = Gtk.Label('Manual mode')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        table.attach(check, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        row += 1

        reg = pld.registers['OUT']
        spin = widgets.PIDSpinButton(pid, 'OUT')
        spin.set_sensitive(False)
        pid.connect('changed', lambda pid, n, val, mult, w=spin: w.set_sensitive(val['A/M']) if n == 'flags' else None)

        label = Gtk.Label('Output level')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        table.attach(spin, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        row += 1

        label = Gtk.Label('Alarm 1')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        pid.connect('changed', lambda pid, n, val, mult, w=label: w.set_text('On' if val['AL1'] else 'Off') if n == 'flags' else None)
        row += 1

        label = Gtk.Label('Alarm 2')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        pid.connect('changed', lambda pid, n, val, mult, w=label: w.set_text('On' if val['AL2'] else 'Off') if n == 'flags' else None)
        row += 1

        label = Gtk.Label('Current Step')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        self.current_step = label
        row += 1

        label = Gtk.Label('Time elapsed/total')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        self.step_time = label
        row += 1

        label = Gtk.Label('Step action')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        label = Gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, row, row+1, yoptions=Gtk.AttachOptions.SHRINK)
        self.status = label
        row += 1

        main_hbox.add(table)

        self.run = True
        self.d = self.loop()
        self.d.addErrback(lambda x: None)
        self.connect('delete-event', self.on_delete)

    def on_restart(self, widget):
        self.restart = True

    def on_delete(self, widget, event):
        self.run = False

    @twisted.internet.defer.inlineCallbacks
    def loop(self):
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

                val, mult = yield self.pid.holding_read('Pr+t')
                step, step_t = val
                val, mult = yield self.pid.holding_read('t-' + ('%02d' % step))
                step_total = 0
                if type(val) is tuple:
                    val, idx = val
                if val == 'Run':
                    step_total = idx
                elif val == 'Jump':
                    val += ' to ' + str(abs(idx))

                self.current_step.set_text(str(step))
                self.step_time.set_text(str(step_t) + '/' + str(step_total) if val == 'Run' else 'NA')
                self.status.set_text(val)

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

                out, mult = yield self.pid.holding_read('OUT')
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
                print 'monitor error', e
                traceback.print_exc(file=sys.stdout)

            d = twisted.internet.defer.Deferred()
            twisted.internet.reactor.callLater(0.300 , d.callback, None)
            yield d


