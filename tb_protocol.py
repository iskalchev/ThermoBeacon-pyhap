'''
Decode Manufacturer specific data from BLE Advertising message

Message length: 20 bytes

bytes | content
========================================================
00-01 | code
02-02 | 00 ?
03-03 | 0x80 if Button is pressed else 00
04-09 | mac address
10-11 | battery level: seems that 3400 = 100% (3400 mV, not quite sure)
12-13 | temperature
14-15 | hummidity
16-19 | uptime: seconds sinse the last reset
'''

MSG_ADVERTISE_DATA   = 1
MSG_ADVERTISE_MINMAX = 2

class TBMessage:
    def __init__(self, msg_type, id, bvalue):
        if id not in [0x10, 0x11]:
            raise ValueError()
        self.msg_type = msg_type
        self.btn = False if bvalue[1]==0 else True
        self.mac = int.from_bytes(bvalue[2:8],byteorder='little')

class TBMsgAdvertise(TBMessage):
    def __init__(self, id, bvalue):
        TBMessage.__init__(self, MSG_ADVERTISE_DATA, id, bvalue)

        self.btr = int.from_bytes(bvalue[8:10],byteorder='little')
        self.btr = self.btr*100/3400
        self.tmp =int.from_bytes(bvalue[10:12],byteorder='little')/16.0
        if self.tmp>4000:
            self.tmp -= 4096
        self.hum = int.from_bytes(bvalue[12:14],byteorder='little')/16.0
        self.upt = int.from_bytes(bvalue[14:18],byteorder='little')


'''
Message length: 22 bytes

bytes | content
========================================================
00-01 | code
02-02 | 00 ?
03-03 | 0x80 if Button is pressed else 00
04-09 | mac address
10-11 | max temp
12-15 | max temp time (s)
16-17 | min temp
18-21 | min temp time (s)
'''

class TBMsgMinMax(TBMessage):
    def __init__(self, id, bvalue):
        TBMessage.__init__(self, MSG_ADVERTISE_MINMAX, id, bvalue)
        
        self.max = int.from_bytes(bvalue[8:10],byteorder='little')/16
        self.max_t = int.from_bytes(bvalue[10:14],byteorder='little')
        self.min = int.from_bytes(bvalue[14:16],byteorder='little')/16.0
        self.min_t = int.from_bytes(bvalue[16:20],byteorder='little')


TB_COMMAND_RESET      = 0x02
TB_COMMAND_TEMP_SCALE = 0x03
TB_COMMAND_IDENTIFY   = 0x04
TB_COMMAND_DUMPALL    = 0x07

