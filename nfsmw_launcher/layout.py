import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class TwoColumnPage(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        self._weights = [0, 0]
        self._columns = [
            Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, valign=Gtk.Align.START)
            for _ in range(2)
        ]
        columns = Gtk.Box(spacing=24, homogeneous=True)
        for column in self._columns:
            columns.append(column)
        self.set_child(
            Adw.Clamp(
                maximum_size=1200,
                tightening_threshold=1000,
                child=columns,
                margin_top=18,
                margin_bottom=18,
                margin_start=24,
                margin_end=24,
            )
        )

    def add(self, group: Gtk.Widget, weight: int = 0, column: int | None = None) -> None:
        if column is None:
            column = 0 if self._weights[0] <= self._weights[1] else 1
        self._weights[column] += weight
        self._columns[column].append(group)
