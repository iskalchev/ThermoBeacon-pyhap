import logging, json, os

import threading, queue,asyncio, time, argparse

from pyhap.accessory import Accessory, Bridge
from pyhap.const import CATEGORY_SENSOR
from pyhap.util import event_wait

from bluepy.btle import DefaultDelegate

import tb_protocol

from tb_config import UDPSrvThread
from tb_btle import *

logger = logging.getLogger('ThermoBeacon')
logger.setLevel(logging.DEBUG)


'''
ThermoBeacon HAP-python accessory class
'''
class ThermoBeacon(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._mac='00:00:00:00:00:00'
        
        self.expire_time = 0

        self.v_temperature = 0
        self.v_humidity = 0
        self.v_batt_level = 0
        self.v_button = False
        self.v_uptime = 0

        service = self.add_preload_service('TemperatureSensor', chars=['StatusLowBattery'])
        
        service.configure_char(
            'CurrentTemperature',
            getter_callback = lambda: self.v_temperature
        )
        service.configure_char(
            'StatusLowBattery',
            getter_callback = self.get_low_battery
        )

        service = self.add_preload_service('BatteryService')
        service.configure_char(
            'StatusLowBattery',
            getter_callback=self.get_low_battery
        )
        charging_state = service.get_characteristic('ChargingState')
        service.configure_char(
            'ChargingState', 
            value=charging_state.properties['ValidValues']['NotChargeable'],
        )
        
        service = self.add_preload_service('HumiditySensor')
        service.configure_char(
            'CurrentRelativeHumidity',
            getter_callback=lambda: self.v_humidity
        )

        self.get_service("AccessoryInformation").get_characteristic("Identify").set_value(1)
        self.get_service("AccessoryInformation").configure_char('Identify', setter_callback=self.set_identify)

    def get_low_battery(self):
        return 0 if self.available else (0 if self.v_batt_level > 15 else 1)

    def get_temperature(self):
        logger.debug('get temperature')
        return self.v_temperature

    def set_identify(self, value):
        for i in range(10):
            try:
                dev = btle.Peripheral(self.mac)
                cmd = '{:02x}'.format(tb_protocol.TB_COMMAND_IDENTIFY)
                write_bytes(dev, cmd)
                dev.disconnect()
                break
            except Exception as exc:
                logger.debug('Exception ' + str(exc))
                pass
            time.sleep(0.2)

    async def run(self):
        t=int(self.expire_time-time.time())
        
        batt_low = 0 if self.v_batt_level > 15 else 1
        
        service = self.get_service('TemperatureSensor')
        service.get_characteristic('CurrentTemperature').set_value(self.v_temperature)
        service.get_characteristic('StatusLowBattery').set_value(batt_low)
        
        service = self.get_service('HumiditySensor')
        service.get_characteristic('CurrentRelativeHumidity').set_value(self.v_humidity)
        
        service = self.get_service('BatteryService')
        service.get_characteristic('BatteryLevel').set_value(self.v_batt_level)
        service.get_characteristic('StatusLowBattery').set_value(batt_low)

    @property
    def available(self):
        t=int(self.expire_time-time.time())
        #logger.debug(self.mac + ' available ' + str(t))
        return True if t>0 else False

    @property
    def mac(self):
        return self._mac
   
    @mac.setter
    def mac(self, value):
       self._mac=value
       self.set_info_service(serial_number=value)

    def parseData(self, data):
        self.v_button      = data.btn
        self.v_batt_level  = data.btr
        self.v_temperature = data.tmp
        self.v_humidity    = data.hum
        self.v_uptime      = data.upt

        self.expire_time = time.time()+90
    
    async def stop(self):
        logger.debug('Stop ' + self.mac)


'''
Derived from Bluepy’s DefaultDelegate
'''
class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

        """ Accessories """
        self.thermo_beacons = dict()

        #helper object - used during device discovery process
        self.discoverDelegate = None

        #pending device for identification
        self.identify_queue=queue.Queue()

    def handleDiscovery(self, dev, isNewDev, isNewData):
        device = self.thermo_beacons.get(dev.addr)
        if device is None and self.discoverDelegate is None:
            return;
        
        complete_name=dev.getValueText(0x09)
        manufact_data=dev.getValueText(0xff)
        if complete_name is None or manufact_data is None:
            return
        bvalue=bytes.fromhex(manufact_data)
        if len(bvalue)!=20 or complete_name!='ThermoBeacon':
            return
        
        if self.discoverDelegate is not None:
            if bvalue[3]==0x80: #if the device's button has been pressed
                self.discoverDelegate.cb_discovered(dev.addr)

        if device is not None:
            msg = tb_protocol.TBMsgAdvertise(bvalue[0]+(bvalue[1]<<8), bvalue[2:])
            device.parseData(msg)          
            
    def addBeacon(self, driver, macAddress, dev_info):
        self.thermo_beacons[macAddress]=ThermoBeacon(driver, display_name = dev_info['name'])
        self.thermo_beacons[macAddress].mac=macAddress
        self.thermo_beacons[macAddress].cfg_name = dev_info['name']
        self.thermo_beacons[macAddress].cfg_aid = dev_info['aid']
        logger.info('Added beacon ' + macAddress + '(' + dev_info['name'] + ')')
        return self.thermo_beacons[macAddress]


class ThermoBeaconBridge(Bridge):
    def __init__(self, driver, config_file):
        super().__init__(driver, display_name='ThermoBeacon Bridge')

        self.update_interval = 10

        self.stop_flag = threading.Event()
        self.scanner_thread = BTScannerThread(event=self.stop_flag, scanDelegate=ScanDelegate())
        
        self.config_file = config_file
        config = self.load_config(config_file)
        #create Accessory objects
        for mac in config:
            beacon = self.scanner_thread.scanDelegate.addBeacon(driver, mac, config[mac])
            if beacon.cfg_aid != -1:
                beacon.aid = beacon.cfg_aid
            self.add_accessory(beacon)

        #Start ScannerThread
        self.scanner_thread.start()

    '''
    Load configuration
    '''
    def load_config(self, file_path):
        config = dict()
        with open(file_path) as cfg_file:
            config_data = json.load(cfg_file)
        for d in config_data:
            config[d['mac']]={'name':d['name'], 'aid':d['aid'] if 'aid' in d else -1}
        return config

    #override Bridge.stop() method
    async def stop(self):
        self.stop_flag.set()
        await super().stop()
    
    #override Bridge.run() method
    async def run(self):
        #start our "configuration server"
        udp_srv_thread = UDPSrvThread(self)
        udp_srv_thread.daemon = True
        udp_srv_thread.start()

        while not await event_wait(self.driver.aio_stop_event, self.update_interval):

            await super().run()

    '''
    method for handling configuration commands
    see: mybeacons.py
    '''
    def processCommand(self, message):
        message = str(message).rstrip('\n')
        logger.debug('Config Message: '+message)
        arg = json.JSONDecoder().decode(message)
        result = 'invalid command'
        if arg['command']=='list':
            result = ''
            devices = self.scanner_thread.scanDelegate.thermo_beacons
            for dev in devices:
                device = devices[dev]
                if device.available:
                    result += '[{0}] AID({1:3d}) T = {2:5.2f}\xb0C, H = {3:3.2f}%, UpTime = {4:6.0f}s [{5}]\n'.\
                             format(device.mac, device.aid, device.v_temperature, device.v_humidity, device.v_uptime, device.cfg_name)
                else:
                    result += '[{0}] AID({1:3d}) - unavailable\n'.format(device.mac, device.aid)
        if arg['command']=='identify':
            devices = self.scanner_thread.scanDelegate.thermo_beacons
            dev = devices.get(arg['mac'])
            if dev:
                result = 'Connection failed.'
                delegate = CmdState(target_mac = dev.mac, identify_timeout = 20)
                self.scanner_thread.scanDelegate.identify_queue.put(delegate)
                if not delegate.stop_event.wait(delegate.identify_timeout):
                    delegate.stop_event.set()
                if delegate.identified:
                    result = 'Identified'
        if arg['command']=='add':
            beacon = self.scanner_thread.scanDelegate.addBeacon(self.driver, arg['mac'], {'name':arg['name'], 'aid':-1})
            self.add_accessory(beacon)
            self.driver.config_changed()
            result = 'added '+arg['mac']
        if arg['command']=='remove':
            devices = self.scanner_thread.scanDelegate.thermo_beacons
            dev = devices.get(arg['mac'])
            if dev:
                del self.accessories[dev.aid]
                del devices[arg['mac']]
            result = 'rmoved ' + arg['mac']
            self.driver.config_changed()
        if arg['command']=='config':
            devices = self.scanner_thread.scanDelegate.thermo_beacons
            data = list()
            for mac in devices:
                dev = devices[mac]
                data.append({'mac':dev.mac, 'name':dev.cfg_name, 'aid':dev.aid})
            str_j = json.dumps(data, indent=4)
            if arg['save']:
                with open(self.config_file, 'w') as cfg_file:
                    cfg_file.write(str_j)
            result = str_j
        if arg['command']=='discover':
            delegate = CmdState()
            result = 'no device discovered'
            self.scanner_thread.scanDelegate.discoverDelegate = delegate
            delegate.stop_event.wait(arg['t'])
            self.scanner_thread.scanDelegate.discoverDelegate = None
            logger.debug('discovered ' + str(delegate.discovered_mac))
            if delegate.discovered_mac is not None:
                if self.add_discovered(delegate.discovered_mac, arg['name']):
                    result = 'device is joined successfully '+str(delegate.discovered_mac)
                else:
                    result = 'cannot add existing device ' + str(delegate.discovered_mac)
             
        return result

    def add_discovered(self, mac, name):
        self.scanner_thread.scanDelegate.discoverDelegate = None
        devices = self.scanner_thread.scanDelegate.thermo_beacons
        result = False
        if devices.get(mac) is None:
            beacon = self.scanner_thread.scanDelegate.addBeacon(self.driver, mac, {'name':name, 'aid':-1})
            self.add_accessory(beacon)
            self.driver.config_changed()
            result = True
        return result

'''
keep the current state of the pending command
- identify device
- discover device
'''
class CmdState:
    def __init__(self, target_mac = None, identify_timeout = None):

        #set to cancel the command
        self.stop_event = threading.Event()

        #discover
        self.discovered_mac = None

        #identify
        self.target_mac = target_mac
        self.identify_timeout = identify_timeout
        self.identified = False

    def cb_discovered(self, mac):
        self.discovered_mac = mac
        self.stop_event.set()
    


