class TBMsgAdvertise:
    def __init__(self, bvalue):
        self.btn = False if bvalue[3]==0 else True
        self.mac = int.from_bytes(bvalue[4:10],byteorder='little')
        self.btr = int.from_bytes(bvalue[10:12],byteorder='little')
        self.btr = self.btr*100/4096
        self.tmp =int.from_bytes(bvalue[12:14],byteorder='little')/16.0
        if self.tmp>4000:
            self.tmp -= 4096
        self.hum = int.from_bytes(bvalue[14:16],byteorder='little')/16.0
        self.upt = int.from_bytes(bvalue[16:20],byteorder='little')
        
