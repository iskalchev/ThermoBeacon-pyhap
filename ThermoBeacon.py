import logging

import threading, time

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
        
        self.time_ticks = 0
        self.time_stamp = 0

        self.v_temperature = 0
        self.v_humidity = 0
        self.v_batt_level = 0
        self.v_button = False
        self.v_uptime = 0

        serv_temp = self.add_preload_service('TemperatureSensor', chars=['StatusLowBattery'])
        
        self.char_temp = serv_temp.configure_char('CurrentTemperature')
        self.char_low_batt = serv_temp.get_characteristic('StatusLowBattery')

        self.battery=self.add_preload_service('BatteryService')
        serv_humidity = self.add_preload_service('HumiditySensor')
        self.char_humidity = serv_humidity.configure_char('CurrentRelativeHumidity')

        self.get_service("AccessoryInformation").get_characteristic("Identify").set_value(1)
        self.get_service("AccessoryInformation").configure_char('Identify', setter_callback=self.set_identify)

    def set_identify(self, value):
        try:
            dev = btle.Peripheral(self.mac)
            write_bytes(dev, '02000000')
            dev.disconnect()
        except Exception as exc:
            logger.debug('Exception ' + str(exc))
            pass
        pass

    async def run(self):
        logger.debug( self.mac + ' ' + str(time.time()-self.time_stamp))

        #if( tmie.time()-self.time_stamp
        #if self.time_ticks>0:
        #    self.time_ticks-=1
        self.char_temp.set_value(self.v_temperature)
        self.char_humidity.set_value(self.v_humidity)
        batt_low = 0 if self.v_batt_level > 15 else 1
        self.battery.get_characteristic('BatteryLevel').set_value(self.v_batt_level)
        self.battery.get_characteristic('StatusLowBattery').set_value(batt_low)
        self.char_low_batt.set_value(batt_low)

    @property
    def available(self):
        #logger.debug('available ' + str(self.time_ticks))
        #return True if self.time_ticks>0 else False
        logger.debug('available ' + str(time.time()-self.time_stamp))
        return True if time.time()-self.time_stamp<90 else False

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

        self.time_stamp = time.time()
    
    async def stop(self):
        logger.debug('Stop ' + self.mac)
        


class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

        """ Accessories """
        self.thermo_beacons = dict()

    def handleDiscovery(self, dev, isNewDev, isNewData):
        device = self.thermo_beacons.get(dev.addr)
        #logger.debug('discobvery:--' + dev.addr + str(device))
        if device is None:
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
            device.parseData(bvalue)
            device.time_ticks=15
 
    def addBeacon(self, driver, macAddress, displayName):
        self.thermo_beacons[macAddress]=ThermoBeacon(driver,displayName)
        self.thermo_beacons[macAddress].mac=macAddress
        logger.info('Added beacon ' + macAddress)
        return self.thermo_beacons[macAddress]


class ThermoBeaconBridge(Bridge):
    def __init__(self, driver, config):
        super().__init__(driver, display_name='ThermoBeacon Bridge')

        self.update_interval = 10
        
        self.stop_flag = threading.Event()
        self.scanner_thread = BTScannerThread(event=self.stop_flag)

        #create Accessory objects
        for mac in config:
            beacon = self.scanner_thread.scanDelegate.addBeacon(driver, mac, config[mac])
            self.add_accessory(beacon)

        #Start ScannerThread
        self.scanner_thread.start()

    async def stop(self):
        self.stop_flag.set()
        await super().stop()

    async def run(self):
        while not await event_wait(self.driver.aio_stop_event, self.update_interval):
            logger.debug('Updating accessories info.')
            await super().run()

class BTScannerThread(threading.Thread):
    def __init__(self, event):
        threading.Thread.__init__(self)
        self.stop_event = event
    
        #for thread synchronization
        self.lock = threading.Lock()

        #self.config=beacons
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
                logger.debug('Exception > ' + str(exc))
                pass
        logger.debug('ScannerThread: exit')

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

