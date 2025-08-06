import QtQuick 2.0
import QtQuick.Controls 1.2

Item {
    id: gaugeBar
    width: 80
    height: 400

    property string imgSrc: "-"
    property real ratio: 0.0
    property int imgHeight: 400

    property int visibleHeight: imgHeight * ratio

    Item {
        id: clipper
        width: parent.width
        height: visibleHeight
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        clip: true

        Behavior on height {
            NumberAnimation {
                duration: 800
                easing.type: Easing.InOutQuad
            }
        }

        Image {
            id: clippedImg
            source: imgSrc
            fillMode: Image.PreserveAspectFit

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
