#include "batteryManager.h"
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <QDebug>
#include <cmath>
#include <algorithm>

BatteryManager::BatteryManager(QObject *parent)
    : QObject(parent) {
    if (init()) {
        connect(&timer, &QTimer::timeout, this, &BatteryManager::updateBattery);
        timer.start(1000); // 1초 간격
    }
}

BatteryManager::~BatteryManager() {
    /*if (i2c_fd >= 0)
        close(i2c_fd);//*/
}

bool BatteryManager::init() {
    /*i2c_fd = open(i2c_device, O_RDWR);
    if (i2c_fd < 0) {
        qWarning() << "I2C open failed";
        return false;
    }

    if (ioctl(i2c_fd, I2C_SLAVE, i2c_address) < 0) {
        close(i2c_fd);
        i2c_fd = -1;
        qWarning() << "I2C ioctl failed";
        return false;
    }//*/

    return true;
}

double BatteryManager::readVoltage() {
    uint8_t buffer[2] = {0};

    /*if (read(i2c_fd, buffer, 2) != 2) {
        qWarning() << "Failed to read voltage";
        return -1;
    }//*/

    int raw = (buffer[0] << 8) | buffer[1];
    return raw * 0.001; // 센서 사양에 맞게 수정
}

int BatteryManager::batteryPercentage() const {
    return m_batteryPercentage;
}

int BatteryManager::convertToPercentage(double voltage) {
    int percentage = static_cast<int>((voltage - 9.0) / (12.6 - 9.0) * 100.0);
    return percentage;//std::clamp(percentage, 0, 100);
}

void BatteryManager::updateBattery() {
    double voltage = readVoltage();
    if (voltage < 0) return;

    int percentage = convertToPercentage(voltage);

    if (percentage != m_batteryPercentage) {
        m_batteryPercentage = percentage;
        emit batteryPercentageChanged();
    }

    qDebug() << "Voltage:" << voltage << "->" << percentage << "%";
}
