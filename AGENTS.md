# Instructions for AI agents

Create badged macOS app icons. This repo puts a badge image (a logo, a "BETA" mark, anything) in an app icon's bottom-right corner, in 14 styles. A user will usually ask you to "run it and give me the link".

## Run the web UI

```bash
git clone https://github.com/dluxhu/dock-icon-badger
cd dock-icon-badger
python3 run.py
```

- Needs only `python3` (3.8+), on macOS or Linux. The first run creates `.venv` and pip-installs `requirements.txt` (Pillow, numpy, cairosvg); this takes up to a minute or two. Later runs start in about a second.
- Run it in the background or a separate terminal: it keeps running until stopped.
- Wait for the line `Dock Icon Badger running at http://127.0.0.1:<port>` and give the user **that exact URL** as a clickable link. The port is 8765 unless it was busy, so always copy it from the output.
- Options: `--open` opens the user's default browser; `--port N` picks a preferred port.
- To get the user started, tell them: click **Samples** under App icons and under Badges (Recommended is preselected), then **Add**. All styles are selected and render automatically; there is no Render button. The "Installed apps" tile works only when the server runs on macOS.
- If you see `Note: SVG inputs are disabled`, tell the user that SVG badges need cairo (`brew install cairo` on macOS, `sudo apt install libcairo2` on Debian/Ubuntu) and that PNG/.icns work meanwhile. After installing cairo, restart the server.
- If `.venv` can't be created on Debian/Ubuntu, `sudo apt install python3-venv` (ask the user first) or install the requirements yourself and run `python3 run.py --no-venv`.

## Stop it

Press Ctrl+C in its terminal, or end the process you started (`kill <pid>`; `run.py` passes the stop on to the server). The server deletes its temporary files on exit. Nothing is installed outside the repo folder.

## Safety notes

- The server binds to 127.0.0.1 only and refuses other `Host` headers. Don't expose it to the network or put it behind a tunnel.
- It never writes outside its temp folder. Local paths typed into the UI are only read, and only icon file types (`.icns`, `.png`, `.svg`, `.jpg`, `.webp`, `.iconset`, `.app`) are accepted.
- The UI doesn't change any installed app's icon. If the user wants that, show them the manual steps in README.md ("Installing an icon") and let them do it, or ask them before running `fileicon` or similar on their apps.

## Command line instead of the UI

```bash
python3 dock_icon_badger.py --apps-dir samples/apps --logo samples/badges/todo-dodo.svg --style all --out out/ --preview
python3 dock_icon_badger.py --list-styles
```

Full spec of every style: `dock-icon-badger.md`.
