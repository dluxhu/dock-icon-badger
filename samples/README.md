# Sample icons

Original artwork for trying Dock Icon Badger, MIT-licensed like the rest of the repo (except the Todo-Dodo logo, see below). The apps are a bright, contemporary set (luminous gradients, crisp white glyphs, translucent glass layers) designed not to resemble Apple's, Google's or anyone's app icons.
Regenerate with `python3 samples/make_samples.py` (needs cairosvg with the cairo library).

| File | What it is | How the generator classifies it |
| --- | --- | --- |
| `apps/Mail.png` | White envelope with a yellow seal dot over a glass second letter, on a full-bleed hot-pink-to-orange square | full-bleed |
| `apps/Calendar.png` | White card with a 3×3 dot grid and one hot-pink checked day over a glass card, on an electric-blue macOS squircle (no text) | macOS-shaped |
| `apps/Notes.png` | Mint page with white lines and a hot-pink pen stroke over a translucent page, on transparency | glyph on white |
| `apps/Swirl.png` | Crisp white spiral with a soft glow on a violet-to-pink macOS squircle | macOS-shaped |
| `apps/Weather.png` | Pale sun behind a glass cloud with an electric-blue droplet, on a sunny yellow macOS squircle | macOS-shaped |
| `apps/Terminal.png` | White prompt and cursor on a glass window, on a full-bleed lime-to-aqua square | full-bleed |
| `apps/Music.png` | Sound-wave capsules in a pink-to-violet gradient over a translucent disc, on transparency | glyph on white |
| `apps/Chat.png` | Translucent electric-blue bubble behind a hot-pink bubble with white dots, on a soft white macOS squircle | macOS-shaped |
| `badges/todo-dodo.svg/.png` | The Todo-Dodo logo | tall badge, blue accent |
| `badges/beta.svg/.png` | Red scalloped seal with heavy "BETA" lettering (letters are drawn as paths) | round badge, red accent |
| `badges/dev.svg/.png` | Green rounded seal with a white `</>` glyph | square badge, green accent |

The UI's sample pickers preselect the recommended set: Mail, Calendar, Notes and Swirl for apps; Todo-Dodo and Beta for badges (see `SAMPLE_META` in `server.py`).

All app icons, the Beta badge and the Dev badge are drawn by `make_samples.py` from SVG shapes written in the script: no third-party icons, images or fonts are used. The only lettering, "BETA", is hand-drawn block-letter paths, so the output doesn't depend on installed fonts. The exception is `badges/todo-dodo.svg`: it is the Todo-Dodo logo, included as a file rather than drawn by code (the PNG is rendered from it). The Todo-Dodo logo belongs to Todo-Dodo, is included with permission as a sample badge, and is not covered by the MIT license.
