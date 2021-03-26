import threading, asyncio, logging
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger('ThermoBeaconSrv')
#logger.setLevel(logging.DEBUG)

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
UDP server, listen for commands on localhost, port 9999
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
