import threading, logging, time
from bluepy import btle

from bluepy.btle import Scanner
import tb_protocol

logger = logging.getLogger('ThermoBeacon')
logger.setLevel(logging.DEBUG)

class BTScannerThread(threading.Thread):
    def __init__(self, event, scanDelegate):
        threading.Thread.__init__(self)

        self.stop_event = event
        self.scanDelegate=scanDelegate

    def run(self):
        while not self.stop_event.wait(2):
            if not self.scanDelegate.identify_queue.empty(): #check for pending identify command
                delegate = self.scanDelegate.identify_queue.get()
                
                time_wait = .25
                cnt = int(delegate.identify_timeout/time_wait)
                logger.debug('identifying: cnt=' + str(cnt) +', timeout = ' + str(delegate.identify_timeout))
                cmd = '{:02x}'.format(tb_protocol.TB_COMMAND_IDENTIFY)
                for i in range(cnt):
                    f, data = btle_sendcmd(delegate.target_mac, cmd)
                    if f:
                        delegate.identified = True
                        delegate.stop_event.set()
                        #logger.debug('identify succeeded ' + data.hex())
                        logger.debug('identify succeeded ')
                        break
                    if delegate.stop_event.wait(time_wait):
                        break
                self.scanDelegate.identify_queue.task_done()

            scanner = Scanner().withDelegate(self.scanDelegate)
            try:
                scanner.clear()
                scanner.start()
                scanner.process(10)
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
    tx.write(write_val, True)
    read_val = rx.read()
    return read_val

######################################################################

def btle_sendcmd(mac, cmd):
    result = False
    data = None
    try:
        conn = btle.Peripheral(mac)
        try: 
           data = write_bytes(conn, cmd)
           result = True
        finally:
            conn.disconnect()
    except Exception as exc:
        logger.debug('sendcmd - ' + str(exc))
        pass
    return result, data
