import QtQuick
import qs.Commons

Column {
  id: root
  property var snapshot: ({devices: [], errors: []})
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  spacing: Style.space(8)
  function icon(kind) { return kind === "mouse" ? "󰍽" : kind === "keyboard" ? "󰌌" : kind === "headphones" ? "󰋋" : "󰂑" }
  function timeLabel(stamp) { return Qt.formatDateTime(new Date(stamp * 1000), "HH:mm") }
  Text { text: "Bateria dos dispositivos"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body + Style.space(2); font.bold: true }
  Text { text: root.snapshot.updatedAt ? "Atualizado às " + root.timeLabel(root.snapshot.updatedAt) + " · a cada minuto" : "Aguardando primeira leitura"; color: root.foreground; opacity: .6; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  Repeater {
    model: root.snapshot.devices
    delegate: Rectangle {
      id: card
      required property var modelData
      width: root.width
      height: info.implicitHeight + Style.space(16)
      radius: Style.space(6)
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .05)
      readonly property bool measured: modelData.percent !== null
      readonly property color levelColor: measured && modelData.percent <= 20 ? Color.urgent : Color.accent
      Column {
        id: info
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        anchors.margins: Style.space(8)
        spacing: Style.space(4)
        Row {
          width: parent.width; spacing: Style.space(7)
          Text { text: root.icon(card.modelData.kind); color: card.levelColor; font.family: root.fontFamily; font.pixelSize: Style.font.body + Style.space(2) }
          Text { width: parent.width - Style.space(82); text: card.modelData.name; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body; elide: Text.ElideRight }
          Text { text: card.measured ? card.modelData.percent + "%" : ""; color: card.levelColor; font.family: root.fontFamily; font.pixelSize: Style.font.body; font.bold: true }
        }
        Rectangle {
          visible: card.measured
          width: parent.width; height: Style.space(3); radius: height / 2
          color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .1)
          Rectangle { width: parent.width * (card.modelData.percent || 0) / 100; height: parent.height; radius: height / 2; color: card.levelColor }
        }
        Text {
          width: parent.width; wrapMode: Text.WordWrap; textFormat: Text.PlainText
          text: card.measured ? (card.modelData.charging ? "Carregando" : "Em uso") + " · " + card.modelData.source : (card.modelData.connected === false ? "Desconectado" : card.modelData.detail || "Bateria não informada") + (card.modelData.lastPercent !== null ? " · última leitura: " + card.modelData.lastPercent + "% às " + root.timeLabel(card.modelData.lastSeen) : "")
          color: root.foreground; opacity: .65; font.family: root.fontFamily; font.pixelSize: Style.font.caption
        }
        Canvas {
          id: graph
          visible: card.modelData.history.length > 1 && card.modelData.history.some(p => p.percent !== card.modelData.history[0].percent)
          width: parent.width; height: visible ? Style.space(18) : 0
          onVisibleChanged: requestPaint()
          Connections { target: card; function onModelDataChanged() { graph.requestPaint() } }
          onPaint: {
            var ctx = getContext("2d"); ctx.clearRect(0, 0, width, height)
            var points = card.modelData.history; if (points.length < 2) return
            var start = points[0].time, span = Math.max(1, points[points.length - 1].time - start)
            ctx.strokeStyle = card.levelColor; ctx.lineWidth = 1.5; ctx.beginPath()
            for (var i = 0; i < points.length; i++) {
              var x = (points[i].time - start) / span * width, y = 2 + (100 - points[i].percent) / 100 * (height - 4)
              if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
            }
            ctx.stroke()
          }
        }
      }
    }
  }
  Text { visible: !root.snapshot.devices.length; text: "Nenhum dispositivo com bateria detectado."; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body }
  Text { width: parent.width; wrapMode: Text.WordWrap; text: "Histórico de 24h · avisos em 20% e 10%.\nBluetooth atualiza quando conectado."; color: root.foreground; opacity: .5; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  Text { visible: root.snapshot.errors.length > 0; width: parent.width; wrapMode: Text.WordWrap; text: root.snapshot.errors.join(" · "); color: Color.urgent; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
}
