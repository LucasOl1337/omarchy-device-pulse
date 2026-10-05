import QtQuick
import QtQuick.Controls
import qs.Commons

Column {
  id: root
  property var snapshot: ({devices: [], errors: []})
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family
  property bool applying: false
  property string actionMessage: ""
  property bool actionFailed: false
  property var focusedEditor: null
  readonly property bool editing: focusedEditor !== null
  property string expandedDevice: ""
  property var dpiDrafts: ({})
  function clearDraft(deviceId) {
    var drafts = Object.assign({}, dpiDrafts)
    delete drafts[deviceId]
    dpiDrafts = drafts
  }
  signal settingRequested(string deviceId, string action, int value)
  spacing: Style.space(8)
  function icon(kind) { return kind === "mouse" ? "󰍽" : kind === "keyboard" ? "󰌌" : kind === "headphones" ? "󰋋" : "󰂑" }
  function timeLabel(stamp) { return Qt.formatDateTime(new Date(stamp * 1000), "HH:mm") }
  Text { text: "DevicePulse · dispositivos"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body + Style.space(2); font.bold: true }
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
      readonly property var settings: modelData.settings || null
      readonly property bool canEdit: settings !== null && settings.canEdit !== false && modelData.settingsLive === true && !root.applying
      readonly property bool expanded: root.expandedDevice === modelData.id
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
        Row {
          visible: card.settings !== null
          width: parent.width; spacing: Style.space(6)
          Text {
            width: parent.width - Style.space(62)
            text: card.settings ? card.settings.dpi + (card.settings.dpiY !== card.settings.dpi ? " × " + card.settings.dpiY : "") + " DPI · " + card.settings.pollingHz + " Hz" + (card.modelData.settingsLive ? "" : " · anterior") : ""
            color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.WordWrap
          }
          Rectangle {
            width: Style.space(56); height: Style.space(20); radius: Style.space(4)
            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .1)
            Text { anchors.centerIn: parent; text: card.expanded ? "Fechar" : "Ajustar"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.expandedDevice = card.expanded ? "" : card.modelData.id }
          }
        }
        Column {
          visible: card.expanded && card.settings !== null
          width: parent.width; spacing: Style.space(6)
          Text { text: "Etapas de DPI"; color: root.foreground; opacity: .55; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
          Flow {
            width: parent.width; spacing: Style.space(4)
            Repeater {
              model: card.settings ? card.settings.stages : []
              delegate: Rectangle {
                required property int modelData
                required property int index
                width: stageText.implicitWidth + Style.space(12); height: Style.space(23); radius: Style.space(4)
                opacity: card.canEdit ? 1 : .45
                color: card.settings && card.settings.stage === index ? Color.accent : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .08)
                Text { id: stageText; anchors.centerIn: parent; text: String(modelData); color: card.settings && card.settings.stage === index ? Color.background : root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
                MouseArea { anchors.fill: parent; enabled: card.canEdit; cursorShape: Qt.PointingHandCursor; onClicked: root.settingRequested(card.modelData.id, "stage", index) }
              }
            }
          }
          Row {
            width: parent.width; spacing: Style.space(6)
            Rectangle {
              width: parent.width - Style.space(92); height: Style.space(27); radius: Style.space(4)
              color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .08)
              TextInput {
                id: dpiInput
                anchors.fill: parent; anchors.margins: Style.space(5)
                text: root.dpiDrafts[card.modelData.id] !== undefined ? root.dpiDrafts[card.modelData.id] : card.settings ? String(card.settings.dpi) : ""
                onTextEdited: {
                  var drafts = Object.assign({}, root.dpiDrafts)
                  drafts[card.modelData.id] = text
                  root.dpiDrafts = drafts
                }
                enabled: card.canEdit; selectByMouse: true
                color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption
                validator: IntValidator { bottom: 50; top: card.settings ? card.settings.maxDpi : 42000 }
                onActiveFocusChanged: {
                  if (activeFocus) root.focusedEditor = dpiInput
                  else if (root.focusedEditor === dpiInput) root.focusedEditor = null
                }
                Keys.onEscapePressed: focus = false
                Keys.onReturnPressed: if (card.canEdit && acceptableInput) root.settingRequested(card.modelData.id, "dpi", parseInt(text))
              }
            }
            Rectangle {
              width: Style.space(86); height: Style.space(27); radius: Style.space(4)
              color: Color.accent; opacity: card.canEdit && dpiInput.acceptableInput ? 1 : .4
              Text { anchors.centerIn: parent; text: root.applying ? "Aplicando…" : "Aplicar DPI"; color: Color.background; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
              MouseArea { anchors.fill: parent; enabled: card.canEdit && dpiInput.acceptableInput; cursorShape: Qt.PointingHandCursor; onClicked: root.settingRequested(card.modelData.id, "dpi", parseInt(dpiInput.text)) }
            }
          }
          Text { text: "Passos de 50 · edita a etapa atual"; color: root.foreground; opacity: .5; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
          Text { text: "Polling rate"; color: root.foreground; opacity: .55; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
          Flow {
            width: parent.width; spacing: Style.space(4)
            Repeater {
              model: [125, 500, 1000, 2000, 4000, 8000]
              delegate: Rectangle {
                required property int modelData
                width: rateText.implicitWidth + Style.space(12); height: Style.space(23); radius: Style.space(4)
                opacity: card.canEdit ? 1 : .45
                color: card.settings && card.settings.pollingHz === modelData ? Color.accent : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, .08)
                Text { id: rateText; anchors.centerIn: parent; text: modelData + " Hz"; color: card.settings && card.settings.pollingHz === modelData ? Color.background : root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
                MouseArea { anchors.fill: parent; enabled: card.canEdit; cursorShape: Qt.PointingHandCursor; onClicked: root.settingRequested(card.modelData.id, "rate", modelData) }
              }
            }
          }
          Text { visible: !card.modelData.settingsLive; width: parent.width; wrapMode: Text.WordWrap; text: "Movimente o mouse e reabra o painel pra atualizar."; color: root.foreground; opacity: .6; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
        }
        Text { visible: !!card.modelData.settingsError; width: parent.width; wrapMode: Text.WordWrap; text: card.modelData.settingsError || ""; color: root.foreground; opacity: .5; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
        Text { visible: card.modelData.kind === "mouse" && !card.settings && card.modelData.id.indexOf("mchose:") !== 0; width: parent.width; text: "Configurações ainda sem suporte"; color: root.foreground; opacity: .45; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
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
  Text { visible: root.actionMessage !== ""; width: parent.width; wrapMode: Text.WordWrap; textFormat: Text.PlainText; text: root.actionMessage; color: root.actionFailed ? Color.urgent : Color.accent; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  Text { width: parent.width; wrapMode: Text.WordWrap; text: "Histórico de 24h · avisos em 20% e 10%.\nBluetooth atualiza quando conectado."; color: root.foreground; opacity: .5; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
  Text { visible: root.snapshot.errors.length > 0; width: parent.width; wrapMode: Text.WordWrap; text: root.snapshot.errors.join(" · "); color: Color.urgent; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
}
