// "v0.0.0"
#include "pdc.h"

pdc::pdc(QObject* parent) : QObject(parent)
{
    connect(&distTimer_, &QTimer::timeout, this, &pdc::sendDistStatus);
    distTimer_.setInterval(300);
}

void pdc::startPDC(){
    if (!distTimer_.isActive()) {
        distTimer_.start();
    }
}

void pdc::stopPDC(){
    distTimer_.stop();
}

void pdc::sendDistStatus(){
    emit pdcValueChanged(distValue);
}

void pdc::pdcValueChangedfromReceiver(float dist){
    distValue = dist;
}
