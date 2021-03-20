"""An example of how to setup and start a ThermoBeacon Bridge.
This is:
1. Create AccessoryDriver Object.
2. Create the ThermoBeacon object and add it to an AccessoryDriver
"""
import logging
import os, signal

from pyhap.accessory_driver import AccessoryDriver

from ThermoBeacon import ThermoBeaconBridge

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

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

