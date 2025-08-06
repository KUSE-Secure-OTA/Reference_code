// "v0.0.0"
#ifndef PDC_H
#define PDC_H

#include <QTimer>
#include <QObject>


class pdc : public QObject
{
    Q_OBJECT
public:
    explicit pdc(QObject *parent = nullptr);
    void sendDistStatus();
signals:
    void pdcValueChanged(float);
public slots:
    void pdcValueChangedfromReceiver(float);
    void startPDC();
    void stopPDC();
private:
    QTimer distTimer_;
    float distValue;

};

#endif // PDC_H
