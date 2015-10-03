from scapy.all import sniff, ARP
from main import main
from datetime import datetime
import time

GATORADE = '74:75:48:41:3c:1c'
SLEEP_INTERVAL = 60 * 2

def arp_capture(pkt):
    if pkt[ARP].op == 1: #who-has (request)
        if pkt[ARP].psrc == '0.0.0.0': # ARP Probe
            if pkt[ARP].hwsrc == GATORADE:
                print '%s: Got a button press! Run the converter!' % datetime.now()
                main.delay()

                # Amazon Dash tries to send a couple of messages
                # so sleep for a bit to ignore them.
                time.sleep(SLEEP_INTERVAL)

def dash():
    sniff(prn=arp_capture, filter="arp", store=0)

if __name__ == '__main__':
    dash()
