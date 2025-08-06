// "v0.0.0"
#include "receiver.h"
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <QDebug>

Receiver::Receiver(QObject *parent):
    QThread(parent), socketCAN(socket(PF_CAN, SOCK_RAW, CAN_RAW)), ifr(), addr(){}

Receiver::~Receiver() {
    close(this->socketCAN);
}

Receiver::Receiver(const Receiver& rcv):
    QThread(rcv.parent()), socketCAN(rcv.socketCAN), ifr(rcv.ifr), addr(rcv.addr), speed_data(rcv.speed_data), dist_data(rcv.dist_data){}

Receiver Receiver::operator=(const Receiver& rcv){
    this->socketCAN = rcv.socketCAN;
    this->addr = rcv.addr;
    this->ifr = rcv.ifr;
    this->speed_data = rcv.speed_data;
    this->dist_data = rcv.dist_data;

    return * this;
}

int Receiver::initialize(){
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

    return SUCCEDED;
}

void Receiver::run(){
    struct can_frame frame;

    qDebug() << "listening for CAN messages on can0...\n";

    while (true) {
        int nbytes = read(socketCAN, &frame, sizeof(struct can_frame));
        if (nbytes < 0) {
            qDebug() << "Error reading CAN frame!\n";
            return;
        }

        //receive data from union
        speed_prev = speed_data.speed_kmh;
        for (int i = 0; i < 4; i++){
            speed_data.bytes[i] = frame.data[i];
        }
        //receive data from union_dist
        dist_prev = dist_data.dist_cm;
        for (int i = 0; i < 4; i++){
            dist_data.bytes[i] = frame.data[i+4];
        }

        //speed filter
        qDebug() << "speed before EMA:" << speed_data.speed_kmh;
        speed_data.speed_kmh = EMA();
        qDebug() << "speed after EMA:" << speed_data.speed_kmh;
        emit speedReceived(speed_data.speed_kmh);   // final speed value?

        //dist filter￩
        qDebug() << "dist before EMA:" << dist_data.dist_cm;
        dist_data.dist_cm = EMA_dist();
        qDebug() << "dist after EMA:" << dist_data.dist_cm;
        emit distanceReceived(dist_data.dist_cm);   // final speed value?

        // Step 5: Process received CAN message
        qDebug() << "Received CAN ID: " << frame.can_id << '\n';
        qDebug() << "Data: " << speed_data.speed_kmh << '\n';
        qDebug() << "Data: " << dist_data.dist_cm << '\n';
        // Step6: Send signal if geara is R

    }
}

float Receiver::EMA(){
    return SMOOTHING_FACTOR * speed_data.speed_kmh + (1 - SMOOTHING_FACTOR) * speed_prev;
}
float Receiver::EMA_dist(){
    return SMOOTHING_FACTOR * dist_data.dist_cm + (1 - SMOOTHING_FACTOR) * dist_prev;
}

