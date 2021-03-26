'''
Decode Manufacturer specific data from BLE Advertising message

Message length: 20 bytes

bytes | content
========================================================
00-02 | 01 00 00
03-03 | 0x80 if Button is pressed else 00
04-09 | mac address
10-11 | battery level: seems that 3400 = 100% (3400 mV, not quite sure)
12-13 | temperature
14-15 | hummidity
16-19 | uptime: seconds sinse the last reset
'''
class TBMsgAdvertise:
    def __init__(self, bvalue):
        self.btn = False if bvalue[3]==0 else True
        self.mac = int.from_bytes(bvalue[4:10],byteorder='little')
        self.btr = int.from_bytes(bvalue[10:12],byteorder='little')
        self.btr = self.btr*100/3400
        self.tmp =int.from_bytes(bvalue[12:14],byteorder='little')/16.0
        if self.tmp>4000:
            self.tmp -= 4096
        self.hum = int.from_bytes(bvalue[14:16],byteorder='little')/16.0
        self.upt = int.from_bytes(bvalue[16:20],byteorder='little')


TB_COMMAND_RESET    = 0x02
TB_COMMAND_IDENTIFY = 0x04
