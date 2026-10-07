import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
  id: root
  moduleName: "lucasol.device-pulse"
  ipcTarget: "lucasol.device-pulse"
  manageIpc: false
  IpcHandler {
    enabled: root.ipcTarget !== ""
    target: root.ipcTarget
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function diagnostics(): string {
      return JSON.stringify({version: "1.2.0", sourceUrl: Qt.resolvedUrl("Panel.qml").toString(), layout: "compact-device-settings", devices: root.snapshot.devices.length})
    }
  }
  property var snapshot: ({devices: [], errors: []})
  property var deferredSnapshot: null
  property string actionMessage: ""
  property bool actionFailed: false
  property string pendingDevice: ""
  readonly property var levels: snapshot.devices.filter(d => d.percent !== null && d.connected === true)
  readonly property int lowest: levels.length ? Math.min.apply(null, levels.map(d => d.percent)) : -1
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function refresh() { if (!refreshProcess.running) refreshProcess.running = true }
  function applySetting(deviceId, action, value) {
    if (controlProcess.running || ["dpi", "stage", "rate", "color"].indexOf(action) < 0) return
    actionMessage = action === "color" ? "Aplicando no teclado…" : "Aplicando no mouse…"
    actionFailed = false
    pendingDevice = deviceId
    controlProcess.command = ["/usr/bin/python3", Quickshell.env("HOME") + "/.config/omarchy/plugins/lucasol.device-pulse/control.py", "--device", deviceId, "--" + action, String(value)]
    controlProcess.running = true
  }
  onOpenedChanged: if (opened) refresh()
  FileView {
    id: status
    path: Quickshell.env("HOME") + "/.local/state/omarchy-device-pulse/status.json"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: {
      try {
        var next = JSON.parse(text())
        if (content.editing) root.deferredSnapshot = next
        else root.snapshot = next
      } catch (e) { console.warn("Baterias: JSON inválido") }
    }
  }
  Connections {
    target: content
    function onEditingChanged() {
      if (!content.editing && root.deferredSnapshot !== null) {
        root.snapshot = root.deferredSnapshot
        root.deferredSnapshot = null
      }
    }
  }
  Process {
    id: refreshProcess
    command: ["systemctl", "--user", "start", "omarchy-device-pulse.service"]
  }
  Process {
    id: controlProcess
    stdout: StdioCollector { id: controlOutput }
    onExited: function(exitCode) {
      try {
        var result = JSON.parse(controlOutput.text)
        root.actionMessage = result.message
        root.actionFailed = !result.ok
        if (result.ok) {
          if (content.focusedEditor) content.focusedEditor.focus = false
          content.clearDraft(root.pendingDevice)
        }
      } catch (error) {
        root.actionMessage = "Não consegui aplicar. Atualize pra conferir o dispositivo."
        root.actionFailed = true
      }
    }
  }
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.lowest < 0 ? "󰂑" : root.lowest <= 20 ? "󰁺" : "󰁹"
    active: root.lowest >= 0 && root.lowest <= 20
    tooltipText: "DevicePulse · bateria e configurações" + (root.lowest >= 0 ? " · menor carga: " + root.lowest + "%" : "")
    onPressed: function(b) { if (b === Qt.MiddleButton) root.refresh(); else root.toggle() }
  }
  KeyboardPanel {
    id: popup
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keys
    contentWidth: popup.fittedContentWidth(Style.space(330))
    contentHeight: popup.fittedContentHeight(content.implicitHeight)
    PanelKeyCatcher {
      id: keys
      blocked: content.editing
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onMoveRequested: function(dx, dy) { scroll.contentY = Math.max(0, Math.min(scroll.contentHeight - scroll.height, scroll.contentY + dy * Style.space(60))) }
      Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        Content {
          id: content
          width: scroll.width - Style.space(6)
          snapshot: root.snapshot
          foreground: root.bar ? root.bar.foreground : Color.foreground
          fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
          applying: controlProcess.running
          actionMessage: root.actionMessage
          actionFailed: root.actionFailed
          onSettingRequested: function(deviceId, action, value) { root.applySetting(deviceId, action, value) }
        }
      }
    }
  }
}
