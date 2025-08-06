// "v0.0.0"
#ifndef SENDER_H
#define SENDER_H

#include <QThread>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <QObject>

class Sender : public QThread
{
    Q_OBJECT

private:
    int socketCAN;
    struct ifreq ifr;
    struct sockaddr_can addr;
    bool isGearR = false;

public:
    static const int SUCCEEDED = 0;
    static const int FAILED = -1;
    

    Sender(QObject *parent = nullptr);
    ~Sender();
    Sender(const Sender& snd);
    Sender operator=(const Sender& snd);

    int initialize();
    void sendMessage(int can_id, const char* data, size_t data_size);

    void run();
public slots:
    void changedGeartoR();
    void changedGeartoNotR();
};

#endif // SENDER_H
