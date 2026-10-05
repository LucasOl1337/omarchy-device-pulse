import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
  id: root
  moduleName: "lucasol.device-pulse"
  manageIpc: false
  property var snapshot: ({devices: [], errors: []})
  readonly property var levels: snapshot.devices.filter(d => d.percent !== null && d.connected === true)
  readonly property int lowest: levels.length ? Math.min.apply(null, levels.map(d => d.percent)) : -1
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function refresh() { if (!refreshProcess.running) refreshProcess.running = true }
  onOpenedChanged: if (opened) refresh()
  FileView {
    id: status
    path: Quickshell.env("HOME") + "/.local/state/omarchy-device-pulse/status.json"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: {
      try { root.snapshot = JSON.parse(text()) } catch (e) { console.warn("Baterias: JSON inválido") }
    }
  }
  Process {
    id: refreshProcess
    command: ["systemctl", "--user", "start", "omarchy-device-pulse.service"]
  }
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.lowest < 0 ? "󰂑" : root.lowest <= 20 ? "󰁺" : "󰁹"
    active: root.lowest >= 0 && root.lowest <= 20
    tooltipText: "Baterias" + (root.lowest >= 0 ? " · menor carga: " + root.lowest + "%" : "")
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
        }
      }
    }
  }
}
