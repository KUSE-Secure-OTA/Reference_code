#ifndef BATTERYMANAGER_H
#define BATTERYMANAGER_H

#include <QObject>
#include <QTimer>

class BatteryManager : public QObject {
    Q_OBJECT
    Q_PROPERTY(int batteryPercentage READ batteryPercentage NOTIFY batteryPercentageChanged)

public:
    explicit BatteryManager(QObject *parent = nullptr);
    ~BatteryManager();

    bool init();
    int batteryPercentage() const;

signals:
    void batteryPercentageChanged();

public slots:
    void updateBattery();

private:
    int i2c_fd;
    const char* i2c_device = "/dev/i2c-1";
    const int i2c_address = 0x40;

    QTimer timer;
    int m_batteryPercentage = 0;

    double readVoltage();
    int convertToPercentage(double voltage);
};

#endif // BATTERYMANAGER_H
