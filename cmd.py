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
import sys
import twisted

coils = [ 'NAT', 'auto', 'manual', 'next', 'pause', 'start', 'end' ]

def action(pid):
    reg = sys.argv[1]
    try:
        reg = int(reg, 0)
    except:
        pass
    if len(sys.argv) > 2:
        val = sys.argv[2]
        d = pid.raw(reg, val)
    elif reg == 'flags':
        d = pid.flags()
    elif reg in coils:
        d = pid.coil(reg)
    else:
        d = pid.holding_read(reg)
    d.addCallback(done)
    d.addErrback(err)

def done(result):
    print result
    twisted.internet.reactor.stop()

def err(error):
    print 'timeout'
    twisted.internet.reactor.stop()

def main():
    port = pld.SerialModbusClient("/dev/ttyUSB0", twisted.internet.reactor, timeout=0.1)
    twisted.internet.reactor.callLater(0, action, port.protocol)
    twisted.internet.reactor.run()

if __name__ == '__main__':
    main()

