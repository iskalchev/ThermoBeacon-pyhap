#!/usr/bin/env python3

'''
Scanner tool for Brifit Bluetooth LE thermometer/hygrometer devices.
Shows the characteristics of the found devices
'''

import sys
from bluepy.btle import Scanner, DefaultDelegate

import tb_protocol

class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            pass
        if True or isNewData:
            #logger.debug('discobvery:' + dev.addr)

            complete_name=dev.getValueText(0x09)
            manufact_data=dev.getValueText(0xff)
            if complete_name is None or manufact_data is None:
                return
            bvalue=bytes.fromhex(manufact_data)
            if len(bvalue)!=20 or complete_name!='ThermoBeacon':
                return

            data = tb_protocol.TBMsgAdvertise(bvalue)
            #print(manufact_data)
            print('MAC:{0}, T= {1:5.2f}\xb0C, H = {2:3.2f}%, Button:{4}, Battery : {5:02.0f}%, UpTime = {3:.0f}s'.\
                  format(dev.addr, data.tmp, data.hum, data.upt, 'On ' if data.btn else 'Off', data.btr))

scanDelegate = ScanDelegate()
scanner = Scanner().withDelegate(scanDelegate)

while True:
    try:
        scanner.clear()
        scanner.start()
        scanner.process(20)
        scanner.stop()
    except Exception as exc:
        #print(str(exc))
        pass
    except KeyboardInterrupt:
        print('\nInterrupted!')
        sys.exit(0)


