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
import time

import matplotlib.figure
import matplotlib.ticker
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

class ATWindow(Gtk.Window):
    def __init__(self, pid):
        Gtk.Window.__init__(self, title="Auto-tune")
        self.pid = pid
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

        self.start = Gtk.Button('Start', Gtk.STOCK_EXECUTE)
        self.start.connect('clicked', self.on_start)
        self.start.set_sensitive(False)
        hbox.pack_start(self.start, False, False, 0)

        self.stop = Gtk.Button('Stop', Gtk.STOCK_STOP)
        self.stop.connect('clicked', self.on_stop)
        self.stop.set_sensitive(False)
        hbox.pack_start(self.stop, False, False, 0)

        button = Gtk.Button('Close', Gtk.STOCK_CLOSE)
        button.connect('clicked', self.on_close)
        hbox.pack_end(button, False, False, 0)

        vbox.add(hbox)

        self.add(vbox)
        self.run = True
        self.start_at = True
        self.stop_at = False
        self.d = self.loop()
        self.d.addErrback(lambda x: None)
        self.connect('delete-event', self.on_delete)

    def on_start(self, widget):
        self.start_at = True

    def on_stop(self, widget):
        self.stop_at = True

    def on_delete(self, widget, event):
        self.run = False

    def on_close(self, widget):
        self.emit('delete-event', None)
        self.destroy()

    @twisted.internet.defer.inlineCallbacks
    def loop(self):
        start = time.time()
        while self.run:
            try:
                d = yield self.pid.flags()
                active = d['AT']
                if active:
                    self.stop.set_sensitive(True)
                    self.start.set_sensitive(False)
                    if self.stop_at:
                        yield self.pid.coil('NAT')

                    pv, mult = yield self.pid.holding_read('PV')
                    self.pv_x.append(time.time() - start)
                    self.pv_y.append(pv)
                    self.pv_plot.set_data(self.pv_x, self.pv_y)
                    self.axes.relim()
                    self.axes.autoscale()
                    self.canvas.draw()

                    sv, mult = yield self.pid.holding_read('dSV')
                    self.sv_x.append(time.time() - start)
                    self.sv_y.append(sv)
                    self.sv_plot.set_data(self.sv_x, self.sv_y)
                    self.axes.relim()
                    self.axes.autoscale()
                    self.canvas.draw()

                    out, mult = yield self.pid.holding_read('OUT')
                    self.out_x.append(time.time() - start)
                    self.out_y.append(out)
                    self.out_plot.set_data(self.out_x, self.out_y)
                    self.out_axes.relim()
                    self.out_axes.autoscale()
                    self.canvas.draw()

                else:
                    self.start.set_sensitive(True)
                    self.stop.set_sensitive(False)
                    if self.start_at:
                        yield self.pid.raw('ModL', 'SV')
                        yield self.pid.raw('At', 'On')
                        start = time.time()
                        self.pv_x = []
                        self.pv_y = []
                        self.sv_x = []
                        self.sv_y = []
                        self.out_x = []
                        self.out_y = []

                self.start_at = False
                self.stop_at = False
            except:
                pass

            d = twisted.internet.defer.Deferred()
            twisted.internet.reactor.callLater(1, d.callback, None)
            yield d

        yield self.pid.coil('NAT')

