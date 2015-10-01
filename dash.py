from scapy.all import sniff, ARP
from main import main

GATORADE = '74:75:48:41:3c:1c'

def arp_capture(pkt):
    if pkt[ARP].op == 1: #who-has (request)
        if pkt[ARP].psrc == '0.0.0.0': # ARP Probe
            if pkt[ARP].hwsrc == GATORADE:
                main.delay()

def dash():
    sniff(prn=arp_capture, filter="arp", store=0)

if __name__ == '__main__':
    dash()
