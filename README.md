# ThermoBeacon-pyhap



[HAP-python](https://github.com/ikalchev/HAP-python) Bridge for Brifit bluetooth thermometer/hygrometer devices

## Table of Contents
1. [Requirements](#Requirements)
2. [Usage](#Usage)
3. [Tools](#Tools)
4. [Supported devices](#Devices)
5. [Useful Links](#Links)

## Requirements <a name="Requirements"></a>

### 1. Install [bluepy Python library](https://github.com/IanHarvey/bluepy)

    $ sudo apt-get install libglib2.0-dev
    $ sudo pip3 install bluepy
    
#### Note:
If you do not want to run your BT scripts as root (or under sudo), you may also give the required capabilities to the bluepy-helper binary, that comes with bluepy. [More details...](https://unix.stackexchange.com/questions/96106/bluetooth-le-scan-as-non-root/182559#182559)

    $ sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/local/lib/python3.7/dist-packages/bluepy/bluepy-helper
### 2. Install [HAP-python](https://github.com/ikalchev/HAP-python)

    $ pip3 install HAP-python

## Usage <a name="Usage"></a>

[Here](https://github.com/ikalchev/HAP-python#run-at-boot-) you can find more details on how to start your service.

Below is an example `hap-python.py` script:

```python
import logging
import os, signal

from pyhap.accessory_driver import AccessoryDriver
from ThermoBeacon import ThermoBeaconBridge

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

service_dir = '~/.hap-python/'

# Start the accessory on port 51826
driver = AccessoryDriver(port=51826,
                         persist_file = service_dir + '.accessory.state',
                         pincode=b'123-12-123')

bridge = ThermoBeaconBridge(driver,
                            config_file = os.path.expanduser(service_dir + 'beacons.json'))

#Run a Bridge
driver.add_accessory(accessory=bridge)

# We want SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)

# Start it!
driver.start()
```

## Config file
JSON encoded list of devices:
```json
[
    {
        "mac": "fa:ac:00:00:11:33",
        "name": "garage",
    },
    {
        "mac": "fa:ac:00:00:11:55",
        "name": "living room",
    }
]
```

## Tools <a name="Tools"></a>
### scan-tool.py
This tool scans for ThermoBeacon BTLE devices and displays useful information about them (mac addrss, current temperature and hummidity, ...)

### mybeacons.py
Command line interface to HAP-python service.

```
$ ./mybeacons.py -h
usage: mybeacons.py [-h] {list,add,remove,identify,config,discover} ...

positional arguments:
  {list,add,remove,identify,config,discover}
                        action
    list                List devices
    add                 Add device
    remove              Remove device
    identify            Identify a device
    config              Save configuration
    discover            Listen for device

optional arguments:
  -h, --help            show this help message and exit

```

## Supported devices <a name="Devices"></a>
[Brifit Bluetooth thermometer and hygrometer, wireless](https://www.amazon.de/-/en/gp/product/B08DLHFKT3/ref=ppx_yo_dt_b_asin_title_o00_s01?ie=UTF8&psc=1)
[ORIA Wireless Thermometer Hygrometer](https://www.amazon.co.uk/dp/B08GKB5D1M/ref=emc_b_5_t)
## Useful Links <a name="Links"></a>
[Python script to scan temperatures and humidity from a Thermobeacon](https://github.com/rnlgreen/thermobeacon)

[Raspberry pi forum thread](https://www.raspberrypi.org/forums/viewtopic.php?f=91&t=283011)
 
[bluepy Python library](https://github.com/IanHarvey/bluepy)
