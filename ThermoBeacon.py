
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR

from bluepy.btle import Scanner, DefaultDelegate
from bluepy import btle

class ThermoBeacon(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mac='00:00:00:00:00:00'
        
        self.time_ticks = 0
        self.v_temperature = 0
        self.v_humidity = 0
        self.v_battery_level = 0

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
        except Exception as inst:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            #print(type(inst), exc_tb.tb_lineno)
            pass
        pass

    @Accessory.run_at_interval(10)
    async def run(self):
        if self.time_ticks>0:
            self.time_ticks-=1
            self.char_temp.set_value(self.v_temperature)
            self.char_humidity.set_value(self.v_humidity)
            #print('time', self.time_ticks)
            batt_low = 0 if self.v_battery_level > 15 else 1
            self.battery.get_characteristic('BatteryLevel').set_value(self.v_battery_level)
            self.battery.get_characteristic('StatusLowBattery').set_value(batt_low)
            self.char_low_batt.set_value(batt_low)

    @property
    def available(self):
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

    def handleDiscovery(self, dev, isNewDev, isNewData):
        #device=self.parent.thermo_beacons.get(dev.addr)
        device = self.worker.getDevice(dev.addr)
        if device is None:
            return;
        if isNewDev:
            pass
            #print( "Discovered device", dev.addr )
        elif isNewData:
            #print( "Received new data from", dev.addr )

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
