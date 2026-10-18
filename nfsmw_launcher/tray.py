import os

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gio, GLib, GdkPixbuf

from .settings_window import ASSETS

WATCHERS = ("org.kde.StatusNotifierWatcher", "org.freedesktop.StatusNotifierWatcher")
TRAY_HELP = (
    "No system tray was found on this desktop. The launcher needs a StatusNotifier tray, "
    "which KDE Plasma, Xfce, Cinnamon, MATE, LXQt, Budgie, waybar and most tray bars provide. "
    "On GNOME, install the AppIndicator extension."
)
_ITEM_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="u" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
    <method name="Scroll"><arg type="i" direction="in"/><arg type="s" direction="in"/></method>
  </interface>
</node>
"""
_MENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <signal name="LayoutUpdated"><arg type="u" name="revision"/><arg type="i" name="parent"/></signal>
  </interface>
</node>
"""


def argb_pixmap(rgba: bytes) -> bytes:
    out = bytearray(len(rgba))
    out[0::4], out[1::4], out[2::4], out[3::4] = rgba[3::4], rgba[0::4], rgba[1::4], rgba[2::4]
    return bytes(out)


def menu_items() -> list[tuple[int, dict[str, str]]]:
    return [
        (1, {"label": "Show Launcher"}),
        (2, {"label": "Launch Game"}),
        (3, {"label": "Redux Settings"}),
        (4, {"type": "separator"}),
        (5, {"label": "Quit"}),
    ]


_ACTIONS = {1: "show", 2: "launch", 3: "settings", 5: "quit"}


def handle_menu_event(item_id: int, event: str, callbacks: dict) -> None:
    if event == "clicked" and item_id in _ACTIONS:
        callbacks[_ACTIONS[item_id]]()


def close_decision(action: str, tray_ok: bool) -> str:
    if action == "quit":
        return "quit"
    return action if tray_ok else "ask"


def _bus() -> Gio.DBusConnection:
    return Gio.bus_get_sync(Gio.BusType.SESSION, None)


def _find_watcher() -> str | None:
    try:
        bus = _bus()
        for name in WATCHERS:
            owned = bus.call_sync(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                "NameHasOwner", GLib.Variant("(s)", (name,)), GLib.VariantType("(b)"),
                Gio.DBusCallFlags.NONE, 1000, None,
            ).unpack()[0]
            if not owned:
                continue
            try:
                host = bus.call_sync(
                    name, "/StatusNotifierWatcher", "org.freedesktop.DBus.Properties", "Get",
                    GLib.Variant("(ss)", (name, "IsStatusNotifierHostRegistered")),
                    GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 1000, None,
                ).unpack()[0]
            except GLib.Error:
                host = True
            if host:
                return name
    except GLib.Error:
        pass
    return None


def tray_available() -> bool:
    return _find_watcher() is not None


def _props(props: dict[str, str]) -> dict[str, GLib.Variant]:
    out = {key: GLib.Variant("s", value) for key, value in props.items()}
    if props.get("type") != "separator":
        out["enabled"] = GLib.Variant("b", True)
    out["visible"] = GLib.Variant("b", True)
    return out


class Tray:
    def __init__(self, callbacks: dict):
        self._callbacks = callbacks
        self._registrations: list[int] = []
        self._owner = 0
        self._bus_connection = None

    def show(self) -> bool:
        if self._registrations:
            return True
        try:
            watcher = _find_watcher()
            if watcher is None:
                return False
            self._bus_connection = bus = _bus()
            item = Gio.DBusNodeInfo.new_for_xml(_ITEM_XML).interfaces[0]
            menu = Gio.DBusNodeInfo.new_for_xml(_MENU_XML).interfaces[0]
            self._registrations = [
                bus.register_object("/StatusNotifierItem", item, self._item_call, self._item_property, None),
                bus.register_object("/MenuBar", menu, self._menu_call, self._menu_property, None),
            ]
            name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
            self._owner = Gio.bus_own_name_on_connection(bus, name, Gio.BusNameOwnerFlags.NONE, None, None)
            bus.call_sync(
                watcher, "/StatusNotifierWatcher", watcher, "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (name,)), None, Gio.DBusCallFlags.NONE, 2000, None,
            )
            return True
        except GLib.Error:
            self.hide()
            return False

    def hide(self) -> None:
        for registration in self._registrations:
            self._bus_connection.unregister_object(registration)
        self._registrations = []
        if self._owner:
            Gio.bus_unown_name(self._owner)
            self._owner = 0

    def _icon(self) -> GLib.Variant:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(ASSETS / "tray.png"))
        width, height = pixbuf.get_width(), pixbuf.get_height()
        pixels = pixbuf.get_pixels()
        if not pixbuf.get_has_alpha():
            pixels = b"".join(pixels[i : i + 3] + b"\xff" for i in range(0, width * height * 3, 3))
        return GLib.Variant("a(iiay)", [(width, height, argb_pixmap(pixels))])

    def _item_property(self, _conn, _sender, _path, _iface, name):
        empty = GLib.Variant("a(iiay)", [])
        values = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "nfsmw-launcher"),
            "Title": GLib.Variant("s", "NFSMW Launcher"),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("u", 0),
            "IconName": GLib.Variant("s", ""),
            "IconPixmap": self._icon(),
            "OverlayIconName": GLib.Variant("s", ""),
            "OverlayIconPixmap": empty,
            "AttentionIconName": GLib.Variant("s", ""),
            "AttentionIconPixmap": empty,
            "AttentionMovieName": GLib.Variant("s", ""),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", ("", [], "NFSMW Launcher", "")),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", "/MenuBar"),
        }
        return values.get(name)

    def _item_call(self, _conn, _sender, _path, _iface, method, _params, invocation):
        if method in ("Activate", "SecondaryActivate"):
            GLib.idle_add(self._callbacks["show"])
        invocation.return_value(None)

    def _menu_property(self, _conn, _sender, _path, _iface, name):
        return {
            "Version": GLib.Variant("u", 3),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status": GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }.get(name)

    def _menu_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        items = menu_items()
        if method == "GetLayout":
            children = [
                GLib.Variant("(ia{sv}av)", (item_id, _props(props), [])) for item_id, props in items
            ]
            root = (0, {"children-display": GLib.Variant("s", "submenu")}, children)
            invocation.return_value(GLib.Variant("(u(ia{sv}av))", (1, root)))
        elif method == "GetGroupProperties":
            invocation.return_value(
                GLib.Variant("(a(ia{sv}))", ([(item_id, _props(props)) for item_id, props in items],))
            )
        elif method == "GetProperty":
            item_id, name = params.unpack()
            props = dict(items).get(item_id, {})
            invocation.return_value(GLib.Variant("(v)", (_props(props).get(name, GLib.Variant("s", "")),)))
        elif method == "Event":
            item_id, event, _data, _time = params.unpack()
            GLib.idle_add(handle_menu_event, item_id, event, self._callbacks)
            invocation.return_value(None)
        elif method == "EventGroup":
            for item_id, event, _data, _time in params.unpack()[0]:
                GLib.idle_add(handle_menu_event, item_id, event, self._callbacks)
            invocation.return_value(GLib.Variant("(ai)", ([],)))
        elif method == "AboutToShow":
            invocation.return_value(GLib.Variant("(b)", (False,)))
        elif method == "AboutToShowGroup":
            invocation.return_value(GLib.Variant("(aiai)", ([], [])))
        else:
            invocation.return_value(None)
