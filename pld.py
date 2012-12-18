#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Russ Dill <Russ.Dill@asu.edu>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

import pymodbus.client.sync
import pymodbus.factory
import pymodbus.client.async
import pymodbus.transaction

import twisted.internet.reactor
import twisted.internet.serialport
import twisted.internet.protocol

from gi.repository import GObject

inty = [ 'T Tc', 'R Tc', 'J Tc', 'Wre3-Wre5', 'B Tc', 'S Tc', 'K Tc', 'E Tc', 'Pt100',
         'Cu50', '0-375Ω', '0-80mV', '0-30mV', '0-5V', '1-5V', '0-10V', '0-10mA', '0-20mA', '4-20mA' ]

alarm_modes = [ 'Program', 'High alarm', 'Low alarm', 'Deviation high alarm', 'Deviation low alarm',
                'Band alarm', 'Deviation high/low alarm', None, None, None, None, None, None, None, None, None,
                'High alarm (w/hold)', 'Low alarm (w/hold)', 'Deviation high alarm (w/hold)',
                'Deviation low alarm (w/hold)', 'Band alarm (w/hold)', 'Deviation high/low alarm (w/hold)' ]

# For SSR, use Duty cycle
output_type = { '0-10mA': 0, '4-20mA': 1, '0-20mA': 2, 'Duty cycle (s)': (3,100) }

run_modes = { 'Energize J1': -1011, 'De-energize J1': -1010, 'Energize J2': -1021, 'De-energize J2': -1020,
              'Jump': (-64,-1), 'Pause': 0, 'Run': (1,9999) }

#    Symbol  Description                           Address   Range           Factory set value

registers = {
    'SV':  ("Set value",                          0x0000,   (-1999,9999),   50,     None),
    'AL1': ("First alarm set value",              0x0001,   (-1999,9999),   60,     None),
    'AL2': ("Second alarm set value",             0x0002,   (-1999,9999),   40,     None),
    'At':  ("Auto tuning ON/OFF",                 0x0003,   ["Off", "On"],"Off",    1.0),

    # Should be able to read the first three in one go.
    'PV':   ("Measured process value",            0x0164,   (-1999,9999),   None,   1.0),
    'dSV':  ("Dynamic set value",                 0x0168,   (-1999,9999),   None,   1.0),
    # NB: Displayed OUT value does not update on write.
    'OUT':  ("Output value",                      0x016C,   (-0.1,100.1),    None,  0.1),
    'Pr+t':("Curve segment number and time",      0x0190,   None,           None,   None),

    'AL1y': ("First alarm type",                  0x1000,   alarm_modes, 'High alarm',1.0),
    'AL1C': ("First alarm hysteresis",            0x1001,   (0,9999),       0,     None),
    'AL2y': ("Second alarm type",                 0x1002,   alarm_modes, 'Low alarm',1.0),
    'AL2C': ("Second alarm hysteresis",           0x1003,   (0,9999),       0,     None),
    # Control output rate (%) is set for measuring range. For wide proportional band,
    # change of control output is small to deviation.
    'P':   ("Proportional band",                  0x1004,   (0.1,300.0),    20,    0.1),
    # The integral function compensates the offset created by proportional action.
    # Effect of compensation is weaker for longer integral time and is intensified by
    # shortening time. Too short integral time causes integrating hunting and may result
    # in wary operation.
    'I':   ("Integral time",                      0x1005,   (0,2000),       100,   1.0),
    # The derivative function improves stability of control by reducing overshooting of
    # integration from expected change of the control output. Effect of compensation is
    # weaker for shorter derivative time and is intensified for longer time. Too longer
    # derivative time may result in oscillating operation.
    'd':   ("Derivative time",                    0x1006,   (0,999),        20,    1.0),
    'Ct':  ("PID proportion cycle",               0x1007,   (0,100),        1,     1.0),#S
    # The SF introduces the integral action separation, overshooting and undershooting are
    # restricted by the action.
    'SF':  ("Anti-reset windup",                  0x1008,   (0,9999),       50,    None),#°C
    # The parameter is against the output jump from PV interference, there is the strongest
    # effect when Pd=0.9 and the weakest when Pd=0.1.
    'Pd':  ("Derivative amplitude limit",         0x1009,   (0.1,0.9),      0.5,   0.1),
    # If PV is in the range of SV±bb, output is computed with PID action, otherwise with
    # ON-OFF action.
    'bb':  ("Range of PID action",                0x100A,   (0,9999),       1000,  1.0),#°C
    'outL': ("Output low limit",                  0x100B,   (0,100.0),      0,     0.1),#%
    'outH': ("Output high limit",                 0x100C,   (0,100.0),      100,   0.1),#%
    'nout': ("Output value when input is abnormal",0x100D,  (0,100),        20,    1.0),#%
    # Added to Pv
    'Psb': ("PV bias",                            0x100E,   (-1999,9999),   0,     None),
    # When it is set to 0, the PV digital filter is turned off. When it is set to 1, 2 or
    # 3, the digital filter action is weaker, medium or stronger, respectively.
    'FILt': ("Digital filter",                    0x100F,   (0,3),          1,     1.0),

    'Inty': ("Input signal type",                 0x2000,   inty,                              'Pt100',1.0),
    'PvL': ("Display low limit",                  0x2001,   (-1999,9999),                      0,      None),
    'PvH': ("Display high limit",                 0x2002,   (-1999,9999),                      500,    None),
    'dot': ("Decimal point position",             0x2003,   (0,3),                             1,      1.0),
    # The reverse action is applied in heating control. If select reverse action (rd=0),
    # output decreases when PV increases and error increases. The direct action is applied
    # in cooling control. If select direct action (rd=1), output decreases when PV
    # decreases and error decreases.
    'rd':  ("Direct/reverse action",              0x2004,   ['reverse action', 'direct action'],'reverse action',1.0),
    'obty': ("Re-transmission output type",       0x2005,   ['0-10mA','4-20mA','0-20mA'],      '0-20mA',1.0),
    'obL': ("Re-transmission low limit",          0x2006,   (-1999,9999),                      0,      None),
    'obH': ("Re-transmission high limit",         0x2007,   (-1999,9999),                      500,    None),
    'oAty': ("Output type",                       0x2008,   output_type,                       '0-20mA',1.0),
    # When input signal is pressure difference (flow measure) and the transducer has no
    # extraction function, this parameter should be set ON. Otherwise should be set OFF.
    'EL':  ("Extraction",                         0x2009,   ['no extraction', 'extraction'],   'no extraction', 1.0),
    # When input signal is pressure difference (flow measure) and small signal removal
    # function is required, SS parameter can be set no zero value. For example, input
    # signal is 4-20mA, set SS to 3 and get [4+(20-4)X3%]=4.48mA, so when input signal
    # is between 4~4.48mA, the input signal is treated with 4mA.
    'SS':  ("Small signal removal",               0x200A,   (0,100),                           0,      1.0),#%
    # In some applications, maximum PID control output (100%) is not permitted. If
    # maximum output (%) is computed soon after reset, this parameter can be set to
    # delay the maximum output. For example, when rES is 80 s and 100% output is
    # computed soon after reset, the output is delayed. The output achieves 100% in
    # 80s after reset.
    'rES': ("Delay startup",                      0x200B,   (0,120),                           0,      1.0),#S
    'uP':  ("Power fail process",                 0x200C,   ['Reset', 'Resume'],               'Resume',1.0), # Reset to PrL, vs Resume last step
    # NB: PID auto tuning function is valid, and P, I, and D in 0036 parameter group is
    # valid (0x1004-0x1006), all parameters in 0037 parameter group are invalid (0x30xx).
    # S-SV: Quit current step according to the setting time (no matter how much the error
    #       between PV and SV). Its unit is second.
    # M-SV: Quit current step according to the setting time (no matter how much the error
    #       between PV and SV). Its unit is minute.
    # S-PV: Quit current step according to SV, and start next step when PV reaches the
    #       current step SV. Its unit is second.
    # M-PV: Quit current step according to SV, start next step when PV reaches the current
    #       step SV. Its unit is minute.
    # SV: constant SV mode. In this mode the SV in 0001 parameter group is object value,
    #     the mode is also called single constant SV mode. In this mode the PID auto tuning
    #     function is valid, and P, I and D in 0036 parameter group is valid, all
    #     parameters in 0037 parameter group are invalid.
    'ModL': ("Work mode",                         0x200D,   [ 'SV', 'S-SV', 'M-SV', 'S-PV', 'M-PV'],'SV',1.0),
    'PrL': ("First step",                         0x200E,   (1,63),                            1,      1.0),
    'PrH': ("Last step",                          0x200F,   (2,64),                            63,     1.0),
    # NB: Manual errors/inconsistencies re the last three entries
    'corf': ("Celsius/Fahrenheit",                0x2010,   ['C', 'F'],                        'C',    1.0),
    'Id':  ("Communication address",              0x2011,   (1,64),                            5,      1.0),
    'bAud': ("Communication baud rate",           0x2012,   ['1200','2400','4800','9600'],     '9600', 1.0),
}

#
# This gist is released under Creative Commons Public Domain Dedication License CC0 1.0
# http://creativecommons.org/publicdomain/zero/1.0/
#

from twisted.internet import defer, reactor

class TimeoutError(Exception):
    """Raised when time expires in timeout decorator"""

def timeout(secs):
    """
    Decorator to add timeout to Deferred calls
    """
    def wrap(func):
        @defer.inlineCallbacks
        def _timeout(*args, **kwargs):
            rawD = func(*args, **kwargs)
            if not isinstance(rawD, defer.Deferred):
                defer.returnValue(rawD)

            timeoutD = defer.Deferred()
            timesUp = reactor.callLater(secs, timeoutD.callback, None)

            try:
                rawResult, timeoutResult = yield defer.DeferredList([rawD, timeoutD], fireOnOneCallback=True, fireOnOneErrback=True, consumeErrors=True)
            except defer.FirstError, e:
                #Only rawD should raise an exception
                assert e.index == 0
                timesUp.cancel()
                e.subFailure.raiseException()
            else:
                #Timeout
                if timeoutD.called:
                    rawD.cancel()
                    raise TimeoutError("%s secs have expired" % secs)

            #No timeout
            timesUp.cancel()
            defer.returnValue(rawResult)
        return _timeout
    return wrap
#
# End gist
#

def ordinal(n):
    if 10 <= n % 100 < 20:
        return str(n) + 'th'
    else:
        return str(n) + {1 : 'st', 2 : 'nd', 3 : 'rd'}.get(n % 10, "th")

for i in range(0, 9):
    step = ordinal(i+1)
    registers['P'+str(i+1)] = (step+' P', 0x3000 + i*3, (0.1,300.0), 20.0, 0.1)
    registers['I'+str(i+1)] = (step+' I', 0x3001 + i*3, (0,2000), 100, 1.0)
    registers['d'+str(i+1)] = (step+' D', 0x3002 + i*3, (0,1000), 20, 1.0)

for i in range(0, 64):
    registers['C-%02d'%(i+1)] = ('PID number of %s step' % step, 0x4000 + i*3, (0,8), 1, 1.0)
    registers['t-%02d'%(i+1)] = ('Run time of %s step' % step, 0x4001 + i*3, run_modes, 0, 1.0)
    registers['Sv%02d'%(i+1)] = ('SV of %s step' % step, 0x4002 + i*3, (-1999,9999), 0, 1.0)

#Note for reprogramming, Slot PrH will not count down.
# Reprogramming
# Set ModL to SV
# Set PrL, PrH
# Program
# coil start
# Set ModL to S-SV

bits = ['SV', 'A/M', 'R/D', 'setting', 'abnormal', 'AL2', 'AL1', 'AT']

bit_desc = {'SV':       'User modifying SV',
            'A/M':      'Manual Control',
            'R/D':      'Heat/cool',
            'setting':  'User modifying settings',
            'abnormal': 'Probe input error',
            'AL2':      'Alarm 2 active',
            'AL1':      'Alarm 1 active',
            'AT':       'Auto-tune active'}

class Set64rs(pymodbus.client.async.ModbusClientProtocol, GObject.GObject):

    __gsignals__ = {
        'changed': (GObject.SIGNAL_RUN_FIRST, None, (str,object,float,)),
        'process-start': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'process-end': (GObject.SIGNAL_RUN_FIRST, None, (str,))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        framer = pymodbus.transaction.ModbusRtuFramer(pymodbus.factory.ClientDecoder())
        pymodbus.client.async.ModbusClientProtocol.__init__(self, framer)
        self.unit_id = 5
        self.reg_iter = registers.iteritems()
        self.is_busy = dict()
        self.queue = list()
        self.last = None

    def busy(self, reg):
        if not reg in self.is_busy:
            self.is_busy[reg] = 0
        self.is_busy[reg] += 1
        if self.is_busy[reg] == 1:
            self.emit('process-start', reg)

    def unbusy(self, reg):
        self.is_busy[reg] -= 1
        if self.is_busy[reg] == 0:
            self.emit('process-end', reg)
        assert self.is_busy[reg] >= 0

    @twisted.internet.defer.inlineCallbacks
    def _flags(self):
        try:
            response = yield timeout(1.0)(self.read_coils)(0, 8, self.unit_id)
            val = dict(zip(bits, response.bits))
            self.emit('changed', 'flags', val, 1.0)
        except TimeoutError, e:
            self.reset()
            raise e
        finally:
            d = twisted.internet.defer.Deferred()
            twisted.internet.reactor.callLater(0.004, d.callback, None)
            yield d
        twisted.internet.defer.returnValue(val)

    def reset(self):
        self.connectionLost('transaction error')
        self.framer._ModbusRtuFramer__buffer = ''
        self.framer._ModbusRtuFramer__header = {}
        self.connectionMade()
        print 'error'

    @twisted.internet.defer.inlineCallbacks
    def _holding_read(self, reg, suppress=False):
        if type(reg) is int:
            register = None
            addr = reg
        else:
            register = registers[reg]
            addr = register[1]
        try:
            response = yield timeout(0.5)(self.read_holding_registers)(addr, 2, self.unit_id)
        except TimeoutError, e:
            self.reset()
            raise e

        mult = 1.0
        if reg == 'Pr+t':
            Pr = response.registers[0]>>8
            t = ((response.registers[0] & 0xff)<<8) + (response.registers[1]>>8)
            val = (Pr, t)
        else:
            value = response.registers[0]
            value = value - 0x10000 if value > 0x7fff else value
            mult = 10**-response.registers[1]
            value *= mult
            if register is None:
                val = value
                reg = '0x%04x' % reg
            else:
                val = None
                if type(register[2]) is tuple:
                    if value >= register[2][0] and value <= register[2][1]:
                        val = value
                    else:
                        pass
                elif type(register[2]) is list:
                    try:
                        val = register[2][value]
                    except:
                        pass
                elif type(register[2]) is dict:
                    for key, item in register[2].iteritems():
                        if type(item) is tuple:
                            if value >= item[0] and value <= item[1]:
                                val = (key, value)
                                break
                        elif item == value:
                            val = key
                            break
        if not suppress:
            self.emit("changed", reg, val, mult)
        d = twisted.internet.defer.Deferred()
        twisted.internet.reactor.callLater(0.004, d.callback, None)
        yield d
        twisted.internet.defer.returnValue((val, mult))

    @twisted.internet.defer.inlineCallbacks
    def _holding_write(self, reg, value):
        register = registers[reg]
        val = None
        if type(register[2]) is tuple:
            if register[2][0] <= float(value) <= register[2][1]:
                val = float(value)
        elif type(register[2]) is list:
            try:
                val = register[2].index(value)
            except:
                pass
        elif type(register[2]) is dict:
            try:
                if type(value) is tuple:
                    value, idx = value
                item = register[2][value]
                if type(item) is tuple:
                    if item[0] <= float(idx) <= item[1]:
                        val = float(idx)
                else:
                    val = item
            except:
                pass

        if val is None:
            raise Exception('invalid argument')
        elif reg == 'OUT':
            d = timeout(0.5)(self.write_registers)(register[1], [int(val*10.0+1), 1], self.unit_id)
        else:
            d = self._holding_read(reg, suppress=True)
            _, mult = yield d
            val /= mult
            if val < 0:
                val += 0x10000
            d = timeout(0.5)(self.write_registers)(register[1], [int(val+1e-6), 0], self.unit_id)

        try:
            yield d
        except TimeoutError, e:
            self.reset()
            raise e

        d = twisted.internet.defer.Deferred()
        twisted.internet.reactor.callLater(0.004, d.callback, None)
        yield d

    @twisted.internet.defer.inlineCallbacks
    def _coil(self, reg):
        # Auto tuning is valid when ModL=SV.
        if reg == 'NAT':
            v = (0, False)
        elif reg == 'auto': # 'A/M'
            v = (1, False)
        elif reg == 'manual':
            v = (1, True)
        elif reg == 'next':
            v = (2, False)
        elif reg == 'pause':
            v = (2, True)
        elif reg == 'start':
            v = (3, False)
        elif reg == 'end':
            v = (3, True)
        else:
            raise Exception('Invalid parameter')

        try:
            yield timeout(0.1)(self.write_coil)(v[0], v[1], self.unit_id)
        except TimeoutError, e:
            pass

    @twisted.internet.defer.inlineCallbacks
    def flags(self):
        self.busy('flags')
        us = twisted.internet.defer.Deferred()
        self.queue.append(us)
        try:
            if len(self.queue) < 2:
                d = twisted.internet.defer.Deferred()
                twisted.internet.reactor.callLater(0, d.callback, None)
                yield d
            else:
                yield self.queue[-2]
            response = yield self._flags()
        finally:
            self.queue.pop(0)
            us.callback(None)
            self.unbusy('flags')
        twisted.internet.defer.returnValue(response)

    @twisted.internet.defer.inlineCallbacks
    def holding_read(self, reg, suppress=False, busy=True):
        if busy:
            self.busy(reg)
        us = twisted.internet.defer.Deferred()
        self.queue.append(us)
        try:
            if len(self.queue) < 2:
                d = twisted.internet.defer.Deferred()
                twisted.internet.reactor.callLater(0, d.callback, None)
                yield d
            else:
                yield self.queue[-2]
            response = yield self._holding_read(reg, suppress)
        finally:
            self.queue.pop(0)
            if busy:
                self.unbusy(reg)
            us.callback(None)
        twisted.internet.defer.returnValue(response)

    @twisted.internet.defer.inlineCallbacks
    def coil(self, cmd):
        us = twisted.internet.defer.Deferred()
        self.queue.append(us)
        try:
            if len(self.queue) < 2:
                d = twisted.internet.defer.Deferred()
                twisted.internet.reactor.callLater(0, d.callback, None)
                yield d
            else:
                yield self.queue[-2]
            response = yield self._coil(cmd)
        finally:
            self.queue.pop(0)
            us.callback(None)

    @twisted.internet.defer.inlineCallbacks
    def raw(self, reg, value):
        self.busy(reg)
        us = twisted.internet.defer.Deferred()
        self.queue.append(us)
        error = False
        try:
            if len(self.queue) < 2:
                d = twisted.internet.defer.Deferred()
                twisted.internet.reactor.callLater(0, d.callback, None)
                yield d
            else:
                yield self.queue[-2]
            try:
                yield self._holding_write(reg, value)
            except:
                pass
            yield self._holding_read(reg)
        finally:
            self.queue.pop(0)
            us.callback(None)
            self.unbusy(reg)

    @twisted.internet.defer.inlineCallbacks
    def holding_write(self, reg, value):
        self.busy(reg)
        us = twisted.internet.defer.Deferred()
        self.queue.append(us)
        error = False
        try:
            if len(self.queue) < 2:
                d = twisted.internet.defer.Deferred()
                twisted.internet.reactor.callLater(0, d.callback, None)
                yield d
            else:
                yield self.queue[-2]
            yield self._holding_write(reg, value)
        finally:
            self.queue.pop(0)
            us.callback(None)
            self.unbusy(reg)

    @twisted.internet.defer.deferredGenerator
    def process_queue(self):
        yield self.queue[-1]

class SerialModbusClient(twisted.internet.serialport.SerialPort):
    def __init__(self, *args, **kwargs):
        self.protocol = Set64rs()
        self.decoder = pymodbus.factory.ClientDecoder()
        twisted.internet.serialport.SerialPort.__init__(self, self.protocol, *args, **kwargs)
        self.flushInput()
