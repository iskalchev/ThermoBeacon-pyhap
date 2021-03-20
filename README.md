# ThermoBeacon-pyhap



[HAP-python](https://github.com/ikalchev/HAP-python) Bridge for Brifit bluetooth thermometer/hygrometer

## Usage
```python
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
```

### Note:
If you do not want to run your BT scripts as root (or under sudo), you may also give the required capabilities to the bluepy-helper binary, that comes with bluepy. [More details...](https://unix.stackexchange.com/questions/96106/bluetooth-le-scan-as-non-root/182559#182559)

sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/lib/python3.7/dist-packages/bluepy/bluepy-helper



 
