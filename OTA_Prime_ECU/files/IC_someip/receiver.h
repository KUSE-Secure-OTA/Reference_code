// "v0.0.0"
#ifndef RECEIVER_H
#define RECEIVER_H

#include <QThread>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <QObject>
union DataUnion {
    float speed_kmh;
    char bytes[4];
};
union DataUnion_dist{
    float dist_cm;
    char bytes[4];
};

class Receiver: public QThread
{

    Q_OBJECT
    Q_PROPERTY(float speedKmh READ getSpeed NOTIFY speedReceived)
    Q_PROPERTY(float distCM READ getDist NOTIFY distanceReceived)

private:
    int socketCAN;
    struct ifreq ifr = ifr;
    struct sockaddr_can addr;
    DataUnion speed_data;
    DataUnion_dist dist_data;

    float speed_prev = 0;
    float dist_prev = 0;

public:
    static const int SUCCEDED = 0;
    static const int FAILED = -1;
    const float SMOOTHING_FACTOR = 0.4;

    Receiver(QObject *parent = nullptr);
    ~Receiver();
    Receiver(const Receiver& rcv);
    Receiver operator=(const Receiver& rcv);
    float getSpeed() const {
        return speed_data.speed_kmh;
    }
    float getDist() const {
        return dist_data.dist_cm;
    }

    float EMA();
    float EMA_dist();

    int initialize();
    void run();

signals:
    void speedReceived(float speedKmh);
    void distanceReceived(float distCm);


};

#endif // RECEIVER_H
