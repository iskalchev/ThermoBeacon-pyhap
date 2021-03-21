import logging, json, os

import threading, asyncio, time, argparse
from concurrent.futures import ThreadPoolExecutor

from pyhap.accessory import Accessory, Bridge
from pyhap.const import CATEGORY_SENSOR
from pyhap.util import event_wait

from bluepy.btle import Scanner, DefaultDelegate
from bluepy import btle

import tb_protocol

logger = logging.getLogger('ThermoBeacon')
logger.setLevel(logging.DEBUG)

        
class ThermoBeacon(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._mac='00:00:00:00:00:00'
        
        self.expire_time = 0

        self.identify_pending = False

        self.v_temperature = 0
        self.v_humidity = 0
        self.v_batt_level = 0
        self.v_button = False
        self.v_uptime = 0

        service = self.add_preload_service('TemperatureSensor', chars=['StatusLowBattery'])
        
        service.configure_char(
            'CurrentTemperature',
            getter_callback = lambda: self.v_temperature
            #properties=self.common_properties
        )
        service.configure_char(
            'StatusLowBattery',
            getter_callback = self.get_low_battery
            #properties=self.common_properties
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
        #logger.debug( self.mac + ' ' + str(t))

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

    def parseData(self, bvalue):
        data = tb_protocol.TBMsgAdvertise(bvalue)
        self.v_button      = data.btn
        self.v_batt_level  = data.btr
        self.v_temperature = data.tmp
        self.v_humidity    = data.hum
        self.v_uptime      = data.upt

        self.expire_time = time.time()+90
    
    async def stop(self):
        logger.debug('Stop ' + self.mac)


class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

        """ Accessories """
        self.thermo_beacons = dict()

        #discover callback
        self.devDiscovered = None

    def handleDiscovery(self, dev, isNewDev, isNewData):
        device = self.thermo_beacons.get(dev.addr)
        #logger.debug('discobvery:--' + dev.addr + str(device))
        if device is None and self.devDiscovered is None:
            return;
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
            
            if self.devDiscovered is not None:
                if bvalue[3]==0x80:
                    self.devDiscovered.discovered(dev.addr)

            if device is not None:
                device.parseData(bvalue)
                if device.identify_pending:
                    device.set_identify(1)
                    device.identify_pending = False

            
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
        self.scanner_thread = BTScannerThread(event=self.stop_flag)

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

    async def stop(self):
        self.stop_flag.set()
        await super().stop()

    async def run(self):
        udp_srv_thread = UDPSrvThread(self)
        udp_srv_thread.daemon = True
        udp_srv_thread.start()

        while not await event_wait(self.driver.aio_stop_event, self.update_interval):
            await super().run()
            
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
                    result += '[{0}] AID({1:3d}) T = {2:5.2f}\xb0C, H = {3:3.2f}%, UpTime = {4:.0f}s [{5}]\n'.\
                             format(device.mac, device.aid, device.v_temperature, device.v_humidity, device.v_uptime, device.cfg_name)
                else:
                    result += '[{0}] AID({1:3d}) - unavailable\n'.format(device.mac, device.aid)
        if arg['command']=='identify':
            devices = self.scanner_thread.scanDelegate.thermo_beacons
            dev = devices.get(arg['mac'])
            if dev:
                logger.debug('------------ '+str(dev))
                result = 'indetifying....' + dev.mac
                dev.identify_pending = True
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
            #self.scanner_thread.scanDelegate.cb_discovery = self.discoveryCallback
            delegate = Discovered(arg['n'], self.discoveryCallback)
            result = 'no device discovered'
            self.scanner_thread.scanDelegate.devDiscovered = delegate
            delegate.stop_event.wait(arg['t'])
            if delegate.result is not None:
                result = 'added device '+str(delegate.result.mac)
            self.scanner_thread.scanDelegate.devDiscovered = None
             
        return result

    def discoveryCallback(self, mac, name):
        logger.debug('discovered - '+str(mac))
        self.scanner_thread.scanDelegate.devDiscovered=None
        devices = self.scanner_thread.scanDelegate.thermo_beacons
        beacon = None
        if devices.get(mac) is None:
            beacon = self.scanner_thread.scanDelegate.addBeacon(self.driver, mac, {'name':name, 'aid':-1})
            self.add_accessory(beacon)
            self.driver.config_changed()
        return beacon

class Discovered:
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.stop_event = threading.Event()
        self.result = None

    def discovered(self, mac):
        self.result = self.callback(mac, self.name)
        self.stop_event.set()

class BTScannerThread(threading.Thread):
    def __init__(self, event):
        threading.Thread.__init__(self)

        self.stop_event = event
        self.scanDelegate=ScanDelegate()

    def run(self):
        while not self.stop_event.wait(5):
            scanner = Scanner().withDelegate(self.scanDelegate)
            try:
                logger.debug('Continue scanning')
                scanner.clear()
                scanner.start()
                scanner.process(20)
                scanner.stop()
            except Exception as exc:
                #logger.debug('Exception > ' + str(exc))
                pass
        logger.debug('ScannerThread: exit')

class ConfigProtocol:
    def __init__(self, command_handler):
        self.command_handler = command_handler
    
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        logger.debug('Received %r from %s' % (message, addr))
        result = self.command_handler.processCommand(message)
        logger.debug('Send %s to %s' % (result, addr))
        self.transport.sendto(bytes(result, 'utf-8'), addr)

'''
echo "test" | socat -t 10 - udp:127.0.0.1:9999
'''
class UDPSrvThread(threading.Thread):
    def __init__(self, bridge):
        threading.Thread.__init__(self)
        self.bridge = bridge

    def run(self):
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor()
        self.loop.set_default_executor(self.executor)
        connect = self.loop.create_datagram_endpoint(
            lambda: ConfigProtocol(self.bridge),
            local_addr=('127.0.0.1', 9999))
        transport, protocol = self.loop.run_until_complete(connect)
        self.loop.run_forever()

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

