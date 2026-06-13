# Howdy GUI

A simple GTK3 frontend for [Howdy](https://github.com/boltgolt/howdy) — Windows Hello style facial authentication for Linux. Manage face models, adjust detection settings, and run tests without the command line.

![Status: Linux-only](https://img.shields.io/badge/platform-Linux-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- **Face models** — list, add and remove registered face models
- **Settings** — adjust timeout, certainty and camera device path
- **Enable/disable** — toggle Howdy authentication on or off
- **Test mode** — run a live recognition test in a terminal window
- **Multi-language** — English and German, switchable in the app with system language auto-detection

## Requirements

[Howdy](https://github.com/boltgolt/howdy) must be installed and configured (`/lib/security/howdy/`).

System packages (Debian/Ubuntu/Mint):

```
sudo apt install python3-gi gir1.2-gtk-3.0 gnome-terminal
```

Fedora:
```
sudo dnf install python3-gobject gtk3 gnome-terminal
```

Arch:
```
sudo pacman -S python-gobject gtk3 gnome-terminal
```

Most actions require `sudo` and will prompt for your password.

## Installation

```
git clone https://github.com/NoCoderGHG/howdy-gui.git
cd howdy-gui
python3 howdy_gui.py
```

No pip dependencies. No virtual environment needed.

## Configuration

Language preference is stored in `~/.config/howdy-gui/config.json`.
Howdy's own settings live in `/lib/security/howdy/config.ini` and are edited directly via `sed`.

## License

MIT — see [LICENSE](LICENSE).
