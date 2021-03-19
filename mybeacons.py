#!/usr/bin/env python3

import sys, re, json, asyncio
from argparse import ArgumentParser, Namespace
 
#print(sys.argv[1:])
 
def mac_addr(x):
    if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", x.lower()):
        raise ValueError()
    return x

 
parser = ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help', dest='command')
 
sub = subparsers.add_parser('list', help = "command_a help")
sub = subparsers.add_parser('add', help = "command_a help")
sub.add_argument('-mac', type=mac_addr, required=True)
sub = subparsers.add_parser('remove', help = "command_a help")
sub = subparsers.add_parser('identify', help = "command_a help")
sub.add_argument('-mac', required=True)
 
args = parser.parse_args(sys.argv[1:])
 
#print('=======')
#parser.print_usage()

js=json.JSONEncoder().encode(vars(args))
#print(js)




'''
'''
class EchoClientProtocol:
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        #print('Send:', self.message)
        self.transport.sendto(self.message.encode())

    def datagram_received(self, data, addr):
        print(data.decode())

        #print("Close the socket")
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        #print("Connection closed")
        self.on_con_lost.set_result(True)
        
'''
'''
async def connect(msg):
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()

    on_con_lost = loop.create_future()
    message = msg #"Hello World!"

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: EchoClientProtocol(message, on_con_lost),
        remote_addr=('127.0.0.1', 9999))

    # Wait until the protocol signals that the connection
    # is lost and close the transport.
    try:
        await on_con_lost
    finally:
        transport.close()


asyncio.run(connect(js))