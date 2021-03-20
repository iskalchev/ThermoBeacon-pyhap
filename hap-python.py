"""An example of how to setup and start a ThermoBeacon Bridge.
This is:
1. Create a dictionary object (or load it from config file) that holds configuration.
   The keys are mac addresses and the values are the beacon names:
      config = {
                  '11:22:00:00:00:01' : 'garage',
                  '33:44:00:00:00:02' : 'living room'
               }
2. Create AccessoryDriver Object.
2. Create the ThermoBeacon object and add it to an AccessoryDriver
"""
import logging
import signal
#import json

import os

from pyhap.accessory_driver import AccessoryDriver

from ThermoBeacon import ThermoBeaconBridge

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")


'''
Load configuration
'''
#def load_config():
#    config = dict()
#    with open(os.path.expanduser('~/.hap-python/beacons.json')) as cfg_file:
#        config_data = json.load(cfg_file)
#    for d in config_data:
#        config[d['mac']]={'name':d['name'], 'aid':d['aid'] if 'aid' in d else -1}
#    return config

#config = load_config()

# Start the accessory on port 51826
driver = AccessoryDriver(port=51826,persist_file='~/.hap-python/.accessory.state', pincode=b'123-12-123')
bridge = ThermoBeaconBridge(driver, config_file = os.path.expanduser('~/.hap-python/beacons.json'))

#Run a Bridge
driver.add_accessory(accessory=bridge)

# We want SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)

# Start it!
driver.start()

