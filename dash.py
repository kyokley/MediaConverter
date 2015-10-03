from scapy.all import sniff, ARP
from main import main
from datetime import datetime

GATORADE = '74:75:48:41:3c:1c'
debounce = True

def arp_capture(pkt):
    global debounce
    if ARP in pkt and pkt[ARP].op == 1: #who-has (request)
        if pkt[ARP].psrc == '0.0.0.0': # ARP Probe
            if pkt[ARP].hwsrc == GATORADE:
                # Amazon Dash tries to send a couple of messages
                # so "debounce" the button presses
                if debounce:
                    print '%s: Got a button press! Run the converter!' % datetime.now()
                    main.delay()
                debounce = not debounce

def dash():
    sniff(prn=arp_capture, filter="arp", store=0)

if __name__ == '__main__':
    dash()
