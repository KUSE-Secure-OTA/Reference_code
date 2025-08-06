// "v0.0.0"
import QtQuick 2.0
import QtGraphicalEffects 1.0

Item {
    id: speedTextComponent
    property int gaugeNumber: 0
    property string gaugeScale: "-"
    property real animatedNumber: 0

    Rectangle {
        id: textBox

        width: 100
        height: 50
        radius: height / 2
        anchors.centerIn: parent
        color: "transparent"
        visible: modeObject.modeValue === "#120102" ? false : true

        RadialGradient {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: modeObject.modeValue }
                GradientStop { position: 0.5; color: "transparent" }
            }
        }
    }

    Text{
        id: numberText
        text: animatedNumber.toFixed(0) //Receiver.speedKmh.toFixed(0)
        font.pixelSize: 70
        color: "white"
        anchors.centerIn: textBox
        //anchors.centerIn: parent
        font.bold: true
    }

    Text{
        id: scaleText
        text: gaugeScale
        font.pixelSize: 25
        color: "white"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: numberText.bottom
        //anchors.topMargin: 10
    }

    Behavior on animatedNumber {
        NumberAnimation {
            duration: 800
            easing.type: Easing.InOutQuad
        }
    }

    onGaugeNumberChanged: {
        let newValue = gaugeNumber
        if (!isNaN(newValue)) {
            animatedNumber = newValue
        }
    }

//    Connections{
//        target: Receiver
//        onSpeedChanged: {
//            speedTextComponent.targetSpeed = Receiver.speedKmh
//            speedAnimation.start()
//        }
//    }



}
