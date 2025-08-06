// "v0.0.0"
// sender.cpp
#include "sender.h"
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <QDebug>

Sender::Sender(QObject *parent):
    QThread(parent), socketCAN(socket(PF_CAN, SOCK_RAW, CAN_RAW)), ifr(), addr(){}

Sender::~Sender() {
    close(this->socketCAN);
}

Sender::Sender(const Sender& snd):
    QThread(snd.parent()), socketCAN(snd.socketCAN), ifr(snd.ifr), addr(snd.addr){}

Sender Sender::operator=(const Sender& snd){
    this->socketCAN = snd.socketCAN;
    this->addr = snd.addr;
    this->ifr = snd.ifr;

    return * this;
}

int Sender::initialize(){
    // Step 1: Create a CAN raw socket
    this-> socketCAN = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (socketCAN < 0) {
        qDebug() << "Error while creating socket!\n";
        return FAILED;
    }

    // Step 2: Specify the CAN interface you want to use (can0)
    std::strcpy(ifr.ifr_name, "can0");
    if (ioctl(socketCAN, SIOCGIFINDEX, &ifr) < 0) {
        qDebug() << "Error getting interface index\n";
        return FAILED;
    }

    // Step 3: Bind the socket to the CAN interface
    std::memset(&addr, 0, sizeof(addr));
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(socketCAN, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        qDebug() << "Error in socket bind!\n";
        return FAILED;
    }

    return SUCCEEDED;
}

void Sender::sendMessage(int can_id, const char* data, size_t data_size) {
    if (data_size == 0) {
        qDebug() << "Data size is 0, no message to send.";
        return;
    }

    if (data_size > 8) {
        qDebug() << "Data size exceeds 8 bytes. Truncating to 8 bytes.";
        data_size = 8; // CAN 데이터 필드는 최대 8바이트
    }

    struct can_frame frame;
    std::memset(&frame, 0, sizeof(frame));
    frame.can_id = can_id;
    frame.can_dlc = data_size;
    std::memcpy(frame.data, data, data_size);

    // 송신
    int nbytes = write(socketCAN, &frame, sizeof(frame));
    if (nbytes < 0) {
        perror("Error sending CAN frame");
        qDebug() << "Failed to send CAN frame with ID: 0x" << QString::number(can_id, 16).toUpper();
    } else if (nbytes < (int)sizeof(frame)) {
        qDebug() << "Incomplete CAN frame sent. Bytes sent:" << nbytes;
    } else {
        qDebug() << "Sent CAN ID: 0x" << QString::number(can_id, 16).toUpper()
                 << ", Data Size:" << frame.can_dlc
                 << ", Data:" << QByteArray::fromRawData((char*)frame.data, frame.can_dlc).toHex(' ');
    }
}


void Sender::run() {

}

void Sender::changedGeartoR(){
    this->isGearR = true;
    qDebug() << "Sender thread is running...";

    const int test_can_id = 0x123; // Example CAN ID
    const char test_data[8] = {0, 0, 0, 0, 0, 0, 0, 1};

    for(int i = 0; i<10; i++) {
        sendMessage(test_can_id, test_data, sizeof(test_data));
        qDebug() << "CAN message sent with ID:" << QString::number(test_can_id, 16).toUpper()
                 << "Data:" << QByteArray::fromRawData((char*)test_data, sizeof(test_data)).toHex(' ');
        // QThread::msleep(100); // Send messages every second
    }
}
void Sender::changedGeartoNotR(){
    this->isGearR = false;
    qDebug() << "Sender thread is running...";

    const int test_can_id = 0x123; // Example CAN ID
    const char test_data[8] = {0, 0, 0, 0, 0, 0, 0, 0};

    for(int i = 0; i<10; i++) {
        sendMessage(test_can_id, test_data, sizeof(test_data));
        qDebug() << "CAN message sent with ID:" << QString::number(test_can_id, 16).toUpper()
                 << "Data:" << QByteArray::fromRawData((char*)test_data, sizeof(test_data)).toHex(' ');
        // QThread::msleep(100); // Send messages every second
    }
}
