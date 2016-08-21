from scapy.all import sniff, ARP, BOOTP
from main import main
from datetime import datetime

from log import LogFile
log = LogFile().getLogger()

GATORADE = '74:75:48:41:3c:1c'

def arp_capture(pkt):
    if ARP in pkt and pkt[ARP].op == 1: #who-has (request)
        if pkt[ARP].psrc == '0.0.0.0': # ARP Probe
            if pkt[ARP].hwsrc == GATORADE:
                log.debug('%s: Got a button press! Run the converter!' % datetime.now())
                main.delay()
    elif BOOTP in pkt and pkt[BOOTP].op == 1:
        if 'src' in pkt.fields and pkt.fields['src'] == GATORADE:
            log.debug('%s: Got a button press! Run the converter!' % datetime.now())
            main.delay()

def dash():
    log.info('Starting up')
    sniff(prn=arp_capture, filter="arp or (port 67 and port 68)", store=0)

if __name__ == '__main__':
    dash()
