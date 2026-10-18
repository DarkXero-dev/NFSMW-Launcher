# NFSMW Launcher

A launcher and settings editor for **Need for Speed: Most Wanted (2005) Redux**.

![Preview](docs/preview.gif)

One click starts the game, and a settings window edits all nine of the Redux mod `.ini` files for you, so you never have to open them by hand.

- **Launch Game** through Bottles, Wine, Proton (umu-run) or your own command.
- **Redux Settings** with every option from the mod's `.ini` files in one place.
- **Close to tray**: closing the window asks whether to quit or minimize to the system tray.
- **Safe edits**: only the values you change are written. A backup is made before the first save.

## Install

1. Download `NFSMW-Launcher.AppImage` from the [latest release](../../releases/latest).
2. Make it executable (`chmod +x NFSMW-Launcher.AppImage`) and run it.
3. On first run, click the cog (top right) and choose how to run the game. The game folder is picked up automatically.

When a newer release is out, an **Update & Relaunch** button appears in the launcher. It downloads the new AppImage, checks it, replaces itself and restarts.

## Notes

- **The game is not included.** For legal reasons it is up to you to find and download it yourself.
- **Primarily built for Arch Linux and derivatives** (CachyOS, EndeavourOS, Manjaro and similar).
