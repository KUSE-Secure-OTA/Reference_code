import QtQuick 2.0

Item {
    Column {
        id: distanceList
        spacing: 15

        Text {
            id: index
            text: "Distance"
            color: "white"

            font.pixelSize: 30
            font.bold: true
        }

        Row {
            spacing: 10

            Text {
                id: distValue
                text: Receiver.distCM.toFixed(1)
                font.pixelSize: 40
                color: "white"
                font.bold: true
            }

            Text {
                id: distScale
                text: "cm"
                color: "white"
                font.pixelSize: 40
            }
        }
    }
}
