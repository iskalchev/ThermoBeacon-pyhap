import logging

import threading

from pyhap.accessory import Accessory, Bridge
from pyhap.const import CATEGORY_SENSOR

from bluepy.btle import Scanner, DefaultDelegate
from bluepy import btle

class ThermoBeacon(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger('ThermoBeacon')
        
        self._mac='00:00:00:00:00:00'
        
        self.time_ticks = 0

        self.v_temperature = 0
        self.v_humidity = 0
        self.v_battery_level = 0
        self.v_button = false
        self.v_uptime = 0

        serv_temp = self.add_preload_service('TemperatureSensor', chars=['StatusLowBattery'])
        
        self.char_temp = serv_temp.configure_char('CurrentTemperature')
        self.battery=self.add_preload_service('BatteryService')
        self.char_low_batt = serv_temp.get_characteristic('StatusLowBattery')
        serv_humidity = self.add_preload_service('HumiditySensor')
        self.char_humidity = serv_humidity.configure_char('CurrentRelativeHumidity')

        self.get_service("AccessoryInformation").get_characteristic("Identify").set_value(1)
        self.get_service("AccessoryInformation").configure_char('Identify', setter_callback=self.set_identify)

    def set_identify(self, value):
        #print('identify')
        try:
            dev = btle.Peripheral(self.mac)
            write_bytes(dev, '02000000')
            dev.disconnect()
        except Exception as exc:
            self.logger.debug('Exception ' + exc)
            pass
        pass

    @Accessory.run_at_interval(10)
    async def run(self):
        self.logger.debug( self.mac + ' ' + str(self.time_ticks))
        if self.time_ticks>0:
            self.time_ticks-=1
            self.char_temp.set_value(self.v_temperature)
            self.char_humidity.set_value(self.v_humidity)
            batt_low = 0 if self.v_battery_level > 15 else 1
            self.battery.get_characteristic('BatteryLevel').set_value(self.v_battery_level)
            self.battery.get_characteristic('StatusLowBattery').set_value(batt_low)
            self.char_low_batt.set_value(batt_low)

    @property
    def available(self):
        self.logger.debug('available ' + str(self.time_ticks))
        return True if self.time_ticks>0 else False

    @property
    def mac(self):
        return self._mac
   
    @mac.setter
    def mac(self, value):
       self._mac=value
       self.set_info_service(serial_number=value)

    #def parseData(self, bvalue):
    #    v_adv=bvalue[3]
    #    v_unkn1=t_tmp=int.from_bytes(bvalue[10:12],byteorder='little')
    #    self.v_temperature = int.from_bytes(bvalue[12:14],byteorder='little')/16.0
    #    if self.v_temperature>4000:
    #        self.v_temperature -= 4096
    #    self.v_humidity = int.from_bytes(bvalue[14:16],byteorder='little')/16.0
    #    t_sec=int.from_bytes(bvalue[16:20],byteorder='little')
    #    v_mac=int.from_bytes(bvalue[4:10],byteorder='little')
    #    #print('{0:012x}'.format(v_mac))
    #    #return v_adv, v_unkn1, t_tmp, t_hum, t_sec



class ScanDelegate(DefaultDelegate):

    def __init__(self):
        DefaultDelegate.__init__(self)

        self.logger = logging.getLogger('ThermoBeacon')
        
        """ Accessories """
        self.thermo_beacons = dict()

    def handleDiscovery(self, dev, isNewDev, isNewData):
        device = self.thermo_beacons.get(dev.addr)
        if device is None:
            return;
        if isNewDev:
            pass
        elif isNewData:
            #self.logger.debug('discobvery:' + dev.addr)

            complete_name=dev.getValueText(0x09)
            manufact_data=dev.getValueText(0xff)
            if complete_name is None or manufact_data is None:
                return
            bvalue=bytes.fromhex(manufact_data)
            if len(bvalue)!=20 or complete_name!='ThermoBeacon':
                return
            #device.parseData(bvalue)
            device.time_ticks=15

            v_adv, v_bat, t_tmp, t_hum, t_sec=parseData20(bvalue)
            device.v_temperature = t_tmp
            device.v_humidity = t_hum
            device.v_battery_level = int( v_bat/4096*100 )
            #print(f'time(s): {t_sec:d}, adv: {v_adv:02x}, temperature: {t_tmp:.2f}, humidity: {t_hum:.1f}, unknown:{v_unkn1:d}')

    def addBeacon(self, driver, macAddress, displayName):
        self.thermo_beacons[macAddress]=ThermoBeacon(driver,displayName)
        self.thermo_beacons[macAddress].mac=macAddress
        self.logger.info('Added beacon ' + macAddress)
        return self.thermo_beacons[macAddress]

def parseData20(bvalue):
    v_adv=bvalue[3]
    v_bat=int.from_bytes(bvalue[10:12],byteorder='little')
    t_tmp=int.from_bytes(bvalue[12:14],byteorder='little')/16.0
    if t_tmp>4000:
        t_tmp -= 4096
    t_hum=int.from_bytes(bvalue[14:16],byteorder='little')/16.0
    t_sec=int.from_bytes(bvalue[16:20],byteorder='little')
    v_mac=int.from_bytes(bvalue[4:10],byteorder='little')
    #print('{0:012x}'.format(v_mac))
    return v_adv, v_bat, t_tmp, t_hum, t_sec


class BTScannerThread(threading.Thread):
    def __init__(self, event, beacons):
        threading.Thread.__init__(self)
        self.stopped = event
    
        self.logger = logging.getLogger('ThermoBeacon')
        self.logger.setLevel(logging.DEBUG)
        
        #for thread synchronization
        self.lock = threading.Lock()

        #remote sensors configuration (TFA units)
        #self.config = dict()

        self.config=beacons
        self.scan_delegate=ScanDelegate()

    def run(self):
        while not self.stopped.wait(5):
            scanner = Scanner().withDelegate(self.scan_delegate)
            try:
                self.logger.debug('start scanning')
                scanner.start()
                scanner.process(25)
                scanner.stop()
            except Exception as exc:
                #self.logger.debug('Exception ' + str(type(exc)))
                self.logger.debug('Exception ' + exc)
                pass
        self.logger.debug('exit thread')

    def get_bridge(self, driver):
        """Call this method to get a Bridge instead of a standalone accessory."""
        bridge = Bridge(driver, 'BT Bridge')
        for mac in self.config:
            beacon = self.scan_delegate.addBeacon(driver, mac, self.config[mac])
            bridge.add_accessory(beacon)
            
        return bridge

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

