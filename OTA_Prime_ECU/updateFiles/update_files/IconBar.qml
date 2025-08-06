import QtQuick 2.0

Item {
    width: 280
    height: 30

    Row {
        id: iconList

        width: parent.width
        height: parent.height

        spacing: 50

        Image {
            id: iconizerheadphoneicon
            x: 247
            y: 158
            width: 25
            height: 25
            source: "images/iconizer-headphone-icon.svg"
            mirror: false
            sourceSize.height: 120
            sourceSize.width: 120
            fillMode: Image.PreserveAspectFit
        }

        Image {
            id: iconizerdaycloudyicon
            x: 351
            y: 156
            width: 30
            height: 30
            source: "images/iconizer-day-cloudy-icon.svg"
            fillMode: Image.PreserveAspectFit
        }

        Image {
            id: iconizergasstationicon
            x: 193
            y: 158
            width: 25
            height: 25
            source: "images/iconizer-gas-station-icon.svg"
            sourceSize.height: 120
            sourceSize.width: 120
            fillMode: Image.PreserveAspectFit
        }

        Image {
            id: iconizeraddresslocationicon
            x: 301
            y: 158
            width: 25
            height: 25
            source: "images/iconizer-address-location-icon.svg"
            sourceSize.height: 120
            sourceSize.width: 120
            fillMode: Image.PreserveAspectFit
        }
    }

}
