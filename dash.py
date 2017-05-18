from scapy.all import sniff, ARP, BOOTP, DHCP
from main import main
from datetime import datetime

from log import LogFile
log = LogFile().getLogger()

GATORADE = '74:75:48:41:3c:1c'
DISCOVER_MESSAGE = ('message-type', 1)

packets = []

def arp_capture(pkt):
    if ARP in pkt and pkt[ARP].op == 1: #who-has (request)
        if pkt[ARP].psrc == '0.0.0.0': # nosec # ARP Probe
            if pkt[ARP].hwsrc == GATORADE:
                log.debug('{}: Got a button press! Run the converter!'.format(datetime.now()))
                main.delay()
    elif BOOTP in pkt and pkt[BOOTP].op == 1:
        if ('src' in pkt.fields and
                pkt.fields['src'] == GATORADE and
                DHCP in pkt and
                DISCOVER_MESSAGE in pkt[DHCP].options):
            log.debug('{}: Got a button press! Run the converter!'.format(datetime.now()))
            main.delay()

def dash():
    log.info('Starting up')
    sniff(prn=arp_capture, filter="arp or port 67", store=0)

if __name__ == '__main__':
    dash()
