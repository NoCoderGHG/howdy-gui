#!/usr/bin/env python3
"""
Howdy GUI - GTK3 frontend for Howdy facial recognition authentication
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import configparser
import json
import locale
import os
import subprocess
from pathlib import Path

CONFIG_DIR  = Path.home() / ".config" / "howdy-gui"
CONFIG_FILE = CONFIG_DIR / "config.json"
I18N_DIR    = Path(__file__).parent / "i18n"

DEFAULT_CONFIG = {"lang": "system"}

HOWDY_CONFIG = "/lib/security/howdy/config.ini"
HOWDY_CLI    = "/lib/security/howdy/cli.py"


# ── Config & i18n ─────────────────────────────────────────────────────────────

def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def detect_system_lang():
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    if not loc:
        loc = os.environ.get("LANG", "")
    return "de" if loc.lower().startswith("de") else "en"


def resolve_lang(setting):
    if setting == "system":
        return detect_system_lang()
    return setting


def load_i18n(lang):
    en = {}
    en_path = I18N_DIR / "en.json"
    if en_path.exists():
        with open(en_path) as f:
            en = json.load(f)
    if lang == "en":
        return en
    path = I18N_DIR / f"{lang}.json"
    if not path.exists():
        return en
    with open(path) as f:
        strings = json.load(f)
    for k, v in en.items():
        strings.setdefault(k, v)
    return strings


def t(strings, key, **kwargs):
    s = strings.get(key, key)
    for k, v in kwargs.items():
        s = s.replace("{" + k + "}", str(v))
    return s


# ── Main window ───────────────────────────────────────────────────────────────

class HowdyGUI(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_border_width(10)
        self.set_default_size(600, 400)

        self.cfg = load_config()
        self.strings = load_i18n(resolve_lang(self.cfg.get("lang", "system")))
        s = self.strings

        self.set_title(t(s, "app_title"))

        # HeaderBar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = t(s, "app_title")
        self.set_titlebar(header)

        self._lang_options = [("de", "lang_de"), ("en", "lang_en"),
                               ("system", "lang_system")]
        self.lang_menu_btn = Gtk.MenuButton()
        self.lang_menu_btn.set_size_request(130, -1)
        self._lang_label = Gtk.Label()
        self.lang_menu_btn.add(self._lang_label)
        lang_menu = Gtk.Menu()
        group = []
        current_lang = self.cfg.get("lang", "system")
        for code, key in self._lang_options:
            item = Gtk.RadioMenuItem.new_with_label(group, t(s, key))
            group = item.get_group()
            if code == current_lang:
                item.set_active(True)
                self._lang_label.set_text(t(s, key))
            item.connect("activate", self._on_lang_menu_item, code)
            lang_menu.append(item)
        lang_menu.show_all()
        self.lang_menu_btn.set_popup(lang_menu)
        header.pack_end(self.lang_menu_btn)

        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)

        self.create_models_tab(notebook)
        self.create_settings_tab(notebook)
        self.create_test_tab(notebook)

        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)
        self.context_id = self.statusbar.get_context_id("status")

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def create_models_tab(self, notebook):
        s = self.strings
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)

        label = Gtk.Label()
        label.set_markup(f"<b>{t(s, 'models_label')}</b>")
        label.set_halign(Gtk.Align.START)
        vbox.pack_start(label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)

        self.model_textview = Gtk.TextView()
        self.model_textview.set_editable(False)
        self.model_textview.set_cursor_visible(False)
        scrolled.add(self.model_textview)
        vbox.pack_start(scrolled, True, True, 0)

        button_box = Gtk.Box(spacing=10)

        refresh_btn = Gtk.Button(label=t(s, "btn_refresh"))
        refresh_btn.connect("clicked", self.on_refresh_models)
        button_box.pack_start(refresh_btn, True, True, 0)

        add_btn = Gtk.Button(label=t(s, "btn_add_face"))
        add_btn.connect("clicked", self.on_add_face)
        button_box.pack_start(add_btn, True, True, 0)

        remove_btn = Gtk.Button(label=t(s, "btn_remove_face"))
        remove_btn.connect("clicked", self.on_remove_face)
        button_box.pack_start(remove_btn, True, True, 0)

        vbox.pack_start(button_box, False, False, 0)

        notebook.append_page(vbox, Gtk.Label(label=t(s, "tab_models")))

        GLib.idle_add(self.on_refresh_models, None)

    def create_settings_tab(self, notebook):
        s = self.strings
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        vbox.set_border_width(10)

        # Timeout
        timeout_box = Gtk.Box(spacing=10)
        timeout_label = Gtk.Label(label=t(s, "lbl_timeout"))
        timeout_label.set_width_chars(20)
        timeout_label.set_halign(Gtk.Align.START)
        self.timeout_spin = Gtk.SpinButton()
        self.timeout_spin.set_adjustment(Gtk.Adjustment(value=2, lower=1, upper=10, step_increment=1))
        timeout_box.pack_start(timeout_label, False, False, 0)
        timeout_box.pack_start(self.timeout_spin, False, False, 0)
        vbox.pack_start(timeout_box, False, False, 0)

        # Certainty
        certainty_box = Gtk.Box(spacing=10)
        certainty_label = Gtk.Label(label=t(s, "lbl_certainty"))
        certainty_label.set_width_chars(20)
        certainty_label.set_halign(Gtk.Align.START)
        self.certainty_spin = Gtk.SpinButton()
        self.certainty_spin.set_adjustment(Gtk.Adjustment(value=4.5, lower=1.0, upper=10.0, step_increment=0.5))
        self.certainty_spin.set_digits(1)
        certainty_box.pack_start(certainty_label, False, False, 0)
        certainty_box.pack_start(self.certainty_spin, False, False, 0)
        vbox.pack_start(certainty_box, False, False, 0)

        # Info
        info_label = Gtk.Label()
        info_label.set_markup(f"<i>{t(s, 'certainty_info')}</i>")
        info_label.set_halign(Gtk.Align.START)
        vbox.pack_start(info_label, False, False, 0)

        # Device path
        device_box = Gtk.Box(spacing=10)
        device_label = Gtk.Label(label=t(s, "lbl_device_path"))
        device_label.set_width_chars(20)
        device_label.set_halign(Gtk.Align.START)
        self.device_entry = Gtk.Entry()
        device_box.pack_start(device_label, False, False, 0)
        device_box.pack_start(self.device_entry, True, True, 0)
        vbox.pack_start(device_box, False, False, 0)

        # Save
        save_btn = Gtk.Button(label=t(s, "btn_save_settings"))
        save_btn.connect("clicked", self.on_save_settings)
        vbox.pack_start(save_btn, False, False, 0)

        # Enable/Disable
        enable_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        enable_box.set_margin_top(20)

        enable_label = Gtk.Label()
        enable_label.set_markup(f"<b>{t(s, 'status_label')}</b>")
        enable_label.set_halign(Gtk.Align.START)
        enable_box.pack_start(enable_label, False, False, 0)

        enable_button_box = Gtk.Box(spacing=10)

        enable_btn = Gtk.Button(label=t(s, "btn_enable"))
        enable_btn.connect("clicked", self.on_enable_howdy)
        enable_button_box.pack_start(enable_btn, True, True, 0)

        disable_btn = Gtk.Button(label=t(s, "btn_disable"))
        disable_btn.connect("clicked", self.on_disable_howdy)
        enable_button_box.pack_start(disable_btn, True, True, 0)

        enable_box.pack_start(enable_button_box, False, False, 0)
        vbox.pack_start(enable_box, False, False, 0)

        notebook.append_page(vbox, Gtk.Label(label=t(s, "tab_settings")))

        GLib.idle_add(self.load_settings)

    def create_test_tab(self, notebook):
        s = self.strings
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)

        label = Gtk.Label()
        label.set_markup(f"<b>{t(s, 'test_title')}</b>")
        vbox.pack_start(label, False, False, 0)

        info = Gtk.Label(label=t(s, "test_info"))
        info.set_line_wrap(True)
        vbox.pack_start(info, False, False, 0)

        test_btn = Gtk.Button(label=t(s, "btn_start_test"))
        test_btn.connect("clicked", self.on_test)
        vbox.pack_start(test_btn, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)

        self.test_textview = Gtk.TextView()
        self.test_textview.set_editable(False)
        self.test_textview.set_cursor_visible(False)
        scrolled.add(self.test_textview)
        vbox.pack_start(scrolled, True, True, 0)

        notebook.append_page(vbox, Gtk.Label(label=t(s, "tab_test")))

    # ── Settings ──────────────────────────────────────────────────────────────

    def load_settings(self):
        s = self.strings
        try:
            config = configparser.ConfigParser()
            config.read(HOWDY_CONFIG)

            if 'video' in config:
                timeout     = config['video'].get('timeout', '2')
                certainty   = config['video'].get('certainty', '4.5')
                device_path = config['video'].get('device_path', '/dev/video0')

                self.timeout_spin.set_value(float(timeout))
                self.certainty_spin.set_value(float(certainty))
                self.device_entry.set_text(device_path)
        except Exception as e:
            self.show_status(t(s, "err_load_settings", e=e))

    def on_refresh_models(self, widget):
        s = self.strings
        try:
            result = subprocess.run(['sudo', 'python3', HOWDY_CLI, 'list'],
                                    capture_output=True, text=True, timeout=15)

            buffer = self.model_textview.get_buffer()
            buffer.set_text(result.stdout if result.stdout else t(s, "no_models_found"))
            self.show_status(t(s, "status_models_refreshed"))
        except Exception as e:
            self.show_status(t(s, "err_generic", e=e))

    def on_add_face(self, widget):
        s = self.strings
        dialog = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=t(s, "dlg_add_face_title"),
        )
        dialog.format_secondary_text(t(s, "dlg_add_face_text"))

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            try:
                subprocess.Popen(['gnome-terminal', '--', 'sudo', 'python3',
                                   HOWDY_CLI, 'add'])
                self.show_status(t(s, "status_add_terminal_opened"))
                GLib.timeout_add_seconds(3, self.on_refresh_models, None)
            except Exception as e:
                self.show_status(t(s, "err_generic", e=e))

    def on_remove_face(self, widget):
        s = self.strings
        dialog = Gtk.Dialog(title=t(s, "dlg_remove_face_title"), parent=self, flags=0)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )

        box = dialog.get_content_area()
        label = Gtk.Label(label=t(s, "lbl_model_id"))
        box.add(label)

        entry = Gtk.Entry()
        box.add(entry)

        dialog.show_all()
        response = dialog.run()
        model_id = entry.get_text()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and model_id:
            try:
                subprocess.run(['sudo', 'python3', HOWDY_CLI,
                                 'remove', model_id, '-y'],
                                capture_output=True, text=True, timeout=15)
                self.show_status(t(s, "status_model_removed", id=model_id))
                self.on_refresh_models(None)
            except Exception as e:
                self.show_status(t(s, "err_generic", e=e))

    def on_save_settings(self, widget):
        s = self.strings
        try:
            timeout     = int(self.timeout_spin.get_value())
            certainty   = self.certainty_spin.get_value()
            device_path = self.device_entry.get_text()

            subprocess.run(['sudo', 'sed', '-i', f's/^timeout = .*/timeout = {timeout}/',
                            HOWDY_CONFIG], check=True, timeout=10)
            subprocess.run(['sudo', 'sed', '-i', f's/^certainty = .*/certainty = {certainty}/',
                            HOWDY_CONFIG], check=True, timeout=10)
            subprocess.run(['sudo', 'sed', '-i', f's|^device_path = .*|device_path = {device_path}|',
                            HOWDY_CONFIG], check=True, timeout=10)

            self.show_status(t(s, "status_settings_saved"))
        except Exception as e:
            self.show_status(t(s, "err_save_settings", e=e))

    def on_enable_howdy(self, widget):
        s = self.strings
        try:
            subprocess.run(['sudo', 'python3', HOWDY_CLI, 'disable', '0'],
                            capture_output=True, timeout=15)
            self.show_status(t(s, "status_howdy_enabled"))
        except Exception as e:
            self.show_status(t(s, "err_generic", e=e))

    def on_disable_howdy(self, widget):
        s = self.strings
        try:
            subprocess.run(['sudo', 'python3', HOWDY_CLI, 'disable', '1'],
                            capture_output=True, timeout=15)
            self.show_status(t(s, "status_howdy_disabled"))
        except Exception as e:
            self.show_status(t(s, "err_generic", e=e))

    def on_test(self, widget):
        s = self.strings
        try:
            subprocess.Popen(['gnome-terminal', '--', 'sudo', 'python3',
                              HOWDY_CLI, 'test'])
            self.show_status(t(s, "status_test_started"))
        except Exception as e:
            self.show_status(t(s, "err_generic", e=e))

    def show_status(self, message):
        self.statusbar.push(self.context_id, message)
        GLib.timeout_add_seconds(5, lambda: self.statusbar.pop(self.context_id))

    def _on_lang_menu_item(self, item, code):
        if not item.get_active(): return
        if code == self.cfg.get("lang"): return
        self.cfg["lang"] = code
        save_config(self.cfg)
        for c, key in self._lang_options:
            if c == code:
                self._lang_label.set_text(t(self.strings, key))
                break
        new_strings = load_i18n(resolve_lang(code))
        dlg = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=t(new_strings, "restart_hint"),
        )
        dlg.run()
        dlg.destroy()


def main():
    win = HowdyGUI()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
