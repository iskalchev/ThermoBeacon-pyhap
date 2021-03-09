"""An example of how to setup and start an Accessory.
This is:
1. Create the Accessory object you want.
2. Add it to an AccessoryDriver, which will advertise it on the local network,
    setup a server to answer client queries, etc.
"""
import logging
import signal

import json
import os
import threading

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
import pyhap.loader as loader
from pyhap.const import CATEGORY_SENSOR

from bluepy.btle import Scanner, DefaultDelegate
from bluepy import btle
import sys

from ThermoBeacon import ThermoBeacon, ScanDelegate

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")





######################################################################

#Transmit Handle 0x0021
TX_CHAR_UUID = btle.UUID('0000fff5-0000-1000-8000-00805F9B34FB')
#Read Handle 0x0024
RX_CHAR_UUID = btle.UUID('0000fff3-0000-1000-8000-00805F9B34FB')

#Function to send a string to the device as a bytearray and return the results received
def write_bytes(dev, vals):
    #Get handles to the transmit and receieve characteristics
    tx = dev.getCharacteristics(uuid=TX_CHAR_UUID)[0]
    rx = dev.getCharacteristics(uuid=RX_CHAR_UUID)[0]
    write_val = bytearray.fromhex(vals)
    tx.write(write_val)
    read_val = rx.read()
    return read_val

######################################################################


class BTTimerThread(threading.Thread):
    def __init__(self, event):
        threading.Thread.__init__(self)
        self.stopped = event

        self.logger = logging.getLogger('ThreadedUDPRequestHandler')

        #for thread synchronization
        self.lock = threading.Lock()

        #Temperature accessories
        self.thermo_beacons=dict()
        #self.acc_hum=dict()

        #remote sensors configuration (TFA units)
        self.config = dict()

        self.scan_delegate=ScanDelegate()
        self.scan_delegate.worker=self

        with open(os.path.expanduser('~/.hap-python/hap_config.json')) as config_file:
            config_data = json.load(config_file)
        for d in config_data:
            self.config[d['mac']]=d['name']
        self.logger.debug('debugdebug')

    def getDevice(self, mac):
        return self.thermo_beacons.get(mac)

    def run(self):
        while not self.stopped.wait(5):
            scanner = Scanner().withDelegate(self.scan_delegate)
            try:
                scanner.start()
                scanner.process(30)
                scanner.stop()
            except Exception as inst:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                #print(type(inst), exc_tb.tb_lineno)
                pass


def get_bridge(driver):
    """Call this method to get a Bridge instead of a standalone accessory."""
    bridge = Bridge(driver, 'BT Bridge')
    config=driver.data_thread.config
    for mac in config:
        driver.data_thread.thermo_beacons[mac]=ThermoBeacon(driver,config[mac])
        driver.data_thread.thermo_beacons[mac].mac=mac
        bridge.add_accessory(driver.data_thread.thermo_beacons[mac])

    return bridge


#def get_accessory(driver):
#    """Call this method to get a standalone Accessory."""
#    return TemperatureSensor(driver, 'MyTempSensor')

stopFlag = threading.Event()
data_thread = BTTimerThread(stopFlag)
data_thread.daemon = True
data_thread.start()

# Start the accessory on port 51826
driver = AccessoryDriver(port=51826,persist_file='~/.hap-python/accessory.state', pincode=b'123-12-123')
driver.data_thread=data_thread
bridge = get_bridge(driver)

# Change `get_accessory` to `get_bridge` if you want to run a Bridge.
#driver.add_accessory(accessory=get_accessory(driver))
driver.add_accessory(accessory=bridge)

# We want SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)

# Start it!
driver.start()
