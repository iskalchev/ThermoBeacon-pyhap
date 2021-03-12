"""An example of how to setup and start an Accessory.
This is:
1. Create the Accessory object you want.
2. Add it to an AccessoryDriver, which will advertise it on the local network,
    setup a server to answer client queries, etc.
"""
import logging
import threading, signal
import json

import os
import sys
#3006129991
from pyhap.accessory_driver import AccessoryDriver
import pyhap.loader as loader

from ThermoBeacon import BTScannerThread

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

def load_config():
    config = dict()
    with open(os.path.expanduser('~/.hap-python/beacons.json')) as cfg_file:
        config_data = json.load(cfg_file)
    for d in config_data:
        config[d['mac']]=d['name']
    return config

config = load_config()
stop_flag = threading.Event()
scanner_thread = BTScannerThread(event=stop_flag, beacons=config)
scanner_thread.daemon = True
scanner_thread.start()

# Start the accessory on port 51826
driver = AccessoryDriver(port=51826,persist_file='~/.hap-python/accessory.state', pincode=b'123-12-123')
bridge = scanner_thread.get_bridge(driver)

#Run a Bridge
driver.add_accessory(accessory=bridge)

# We want SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
#signal.signal(signal.SIGTERM, driver.signal_handler)
def signal_handler(_signal, _frame):
    stop_flag.set()
    driver.signal_handler(_signal, _frame)
    
signal.signal(signal.SIGTERM, signal_handler)

# Start it!
driver.start()
