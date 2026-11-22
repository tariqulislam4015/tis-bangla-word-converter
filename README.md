<p align="center"><img src="assets/icons/tis_logo_256.png" width="96" alt="TIS logo"></p>

<h1 align="center">TIS (Bangla Word Converter)</h1>

<p align="center"><b>Smart Bengali Text &amp; Document Conversion</b><br>
Unicode ⇄ Bijoy &nbsp;|&nbsp; SolaimanLipi ⇄ SutonnyMJ</p>

<p align="center">
<a href="https://tariqulislam4015.github.io/tis-bangla-word-converter/"><b>Live Demo</b></a> &nbsp;•&nbsp;
<a href="https://github.com/tariqulislam4015/tis-bangla-word-converter/releases/latest"><b>Download for Windows</b></a> &nbsp;•&nbsp;
<a href="#developer">Developer</a>
</p>

TIS is a Windows desktop program for Bangladeshi teachers, question setters, publishers and office staff. It converts Bengali between **Unicode** (SolaimanLipi, Nirmala UI, Kalpurush …) and **Bijoy ANSI** (SutonnyMJ), for typed text and whole Word documents, in **both directions**.

**Only the Bengali text changes.** Equations, images, tables, English text, numbers, formatting and page setup are copied unchanged. Inside the .docx package, every part except the text part is copied byte for byte from your original file.

## Live Demo

**[https://tariqulislam4015.github.io/tis-bangla-word-converter/](https://tariqulislam4015.github.io/tis-bangla-word-converter/)**

Type or paste text, or drop a Word file, and the result downloads at once. The page runs the program's own Python conversion engine inside your browser (via Pyodide), so files never leave your computer.

## Download

| File | Use |
|---|---|
| [**TIS_Bangla_Word_Converter_Setup.exe**](https://github.com/tariqulislam4015/tis-bangla-word-converter/releases/latest/download/TIS_Bangla_Word_Converter_Setup.exe) | Installer, with a Start Menu shortcut and an uninstaller. Share this one. |
| [**TIS_Bangla_Word_Converter_Portable.zip**](https://github.com/tariqulislam4015/tis-bangla-word-converter/releases/latest/download/TIS_Bangla_Word_Converter_Portable.zip) | No installation. Unzip and run, even from a USB stick. |

Windows 10 or 11 (64-bit). Python is not needed. The first time you run it, Windows may show "Windows protected your PC". Click **More info → Run anyway**. To see Bijoy text properly, install the SutonnyMJ font (not included, because it is commercially licensed).

## Features

- **Word documents, both directions.** Choose **Unicode → Bijoy** or **Bijoy → Unicode** under *Conversion type*, then drop a .docx. It converts at once and saves next to the original (`Exam_Unicode.docx` → `Exam_Bijoy.docx`). The original is never overwritten.
- **Safe for question papers.** Equations stay exactly as they are by default, and so do images, tables, English text, headers, footers and text boxes.
- **Batch conversion.** Many .docx and .txt files, or whole folders, each saved in its own folder.
- **Text converter.** Live conversion while you type, Bijoy ⇄ Unicode, and copy to Word with fonts kept.
- **Accurate Bengali.** Conjuncts, reph, র-ফলা, য-ফলা, ব-ফলা and vowel signs are placed in the right order (কর্তৃক → `KZ©„K`, রাষ্ট্র → `ivóª`, দৈর্ঘ্য → `ˆ`N©¨`).
- **Animated welcome screen** with the developer's photo, links and voice. Light and dark themes, history, recent files and keyboard shortcuts.

<p align="center"><img src="docs/screenshots/welcome.png" width="300" alt="TIS welcome screen"></p>

## How the conversion works

Unicode stores Bengali in **logical** order (consonant, then vowel sign). Bijoy stores it in **visual** order, with the glyph codes of SutonnyMJ. The engine (`core/unicode_to_bijoy.py`) works in these steps:

1. **Splits** the text into Bengali and non-Bengali segments. English, ASCII digits, maths, and symbols are passed through untouched.
2. **Normalizes** equivalent encodings (decomposed ড়/য়, split ো/ৌ, chandrabindu typed before a kar, and similar).
3. **Parses each syllable** once, left to right: `[reph] consonant(্consonant)* [vowel signs] [ঁ]`.
4. **Renders the syllable in visual order**: pre-base kar (ি ে ৈ), then the conjunct (longest match in a 200+ entry ligature table), then phalas (র-ফলা, য-ফলা, ব-ফলা), then the reph `©`, then post-base kars, then `u` (ঁ).
5. **Chooses glyph variants from context**: u-kar `y/z/æ/–`, ū-kar `~/‚/ƒ`, ri-kar `„/…`, r-phala `Ö/ª/«`, word-initial e/oi-kar `†/ˆ` versus medial `‡/‰`, and ligatures such as গু `¸`, শু `ï`, হু `û`, হৃ `ü`, ন্তু `š‘`.
6. **Falls back safely**: a conjunct with no SutonnyMJ ligature is written with a visible hasanta (`&`), and the report says so, so no text is ever dropped.
7. Applies optional **user correction rules**: exact replacements on the Bijoy output of Bengali segments only.

Examples: `আমার সোনার বাংলা → Avgvi †mvbvi evsjv`, `কর্তৃক → KZ©„K`, `রাষ্ট্র → ivóª`, `দৈর্ঘ্য → ˆ`N©¨`, `শিক্ষা → wk¶v`.

### Accuracy
The engine is checked against a reference corpus of 103 test cases (about 200 words, including full exam sentences) covering vowels, consonants, every kar, reph, r-, y-, and b-phala, common and three-part conjuncts, numerals, punctuation, and mixed English and Bengali. It is also round-trip tested (Unicode → Bijoy → Unicode). **No converter can promise 100% accuracy:** SutonnyMJ has no glyph for some rare conjuncts, and publishers differ on a few glyph variants. Use the highlight option to proofread important documents, and add correction rules for house styles.

### Document handling details and limitations
* Bengali is detected by its Unicode characters, not by font name. Runs that inherit their font from a style are converted too.
* A syllable split across two runs (common after spell-check or partial bold) is re-joined into the run where it starts, so reordering stays correct.
* Mixed runs (Bengali + English) are split: only the Bengali part gets SutonnyMJ (`w:ascii`, `w:hAnsi`, `w:cs`).
* Bold, italic, or size set only for complex scripts (`w:bCs`, `w:iCs`, `w:szCs`) is copied to the regular properties, because Bijoy text is not complex-script text.
* **Not converted:** text inside images, WordArt, charts, SmartArt graphics, and embedded objects. Old `.doc` files must be saved as `.docx` first. Tracked deletions are left as they are.

---


## Developer guide

### Run from source
```bash
git clone https://github.com/tariqulislam4015/tis-bangla-word-converter.git
cd tis-bangla-word-converter
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\activate
```
Install and run:
```bash
pip install -r requirements.txt
python main.py
```

### Tests
```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```
`tests/test_gui.py` runs the real Qt interface headlessly (`QT_QPA_PLATFORM=offscreen`). It is skipped if PySide6 is not installed. `python main.py --self-test` performs a start-up check that returns exit code 0 or 1.

### Build the EXE and installer
On Windows with Python 3.10+ (and [Inno Setup 6](https://jrsoftware.org/isinfo.php) for the installer):
```bat
packaging\build_windows.bat
```
This produces, in `release\`:
* `TIS_Bangla_Word_Converter_Setup.exe`: the installer
* `TIS_Bangla_Word_Converter_Portable.zip`: the portable version (EXE, `portable.ini`, licence, readme)
* `TIS_Bangla_Word_Converter.exe`: the single-file EXE

**Without a Windows build machine:** push the project to GitHub. The workflow `.github/workflows/build-windows.yml` tests on Python 3.10 and 3.12, builds both packages, self-tests the built EXEs headlessly, and uploads them as the **TIS-Windows** artifact. Pushing a tag such as `v1.0.0` attaches them to a GitHub Release.

### Project structure
```
main.py                     entry point (logging, splash, crash handler, --self-test)
config/settings.py          app identity, paths, persisted settings, portable mode
core/
  conversion_rules.py       SutonnyMJ glyph tables (consonants, kars, conjuncts, variants)
  unicode_to_bijoy.py       conversion engine (segment → syllable → visual order)
  bijoy_to_unicode.py       reverse decoder (text mode + round-trip tests)
  correction_rules.py       normalisation rules + user correction rules (JSON)
  text_utils.py             Bengali/foreign segmentation, statistics
  font_detector.py          SutonnyMJ detection (registry + font folders)
services/
  docx_service.py           Unicode -> Bijoy DOCX conversion (all story parts; only changed parts rewritten)
  docx_b2u.py               Bijoy -> Unicode DOCX conversion (finds SutonnyMJ text via run/style/default fonts)
  txt_service.py            encoding-aware text I/O (UTF-8/UTF-16/ANSI), atomic saves
  batch_service.py          batch runner with cancel and per-file results
  history_service.py        SQLite history
  export_service.py         text → .docx export with per-segment fonts
  file_naming.py            *_Unicode → *_Bijoy naming, collision-free paths
ui/                         PySide6 interface (main_window, pages, dialogs, theme, styles, icons, workers)
assets/                     icon (.ico), logo, splash
packaging/                  PyInstaller specs, version resource, Inno Setup script, build script, make_assets.py
tests/                      corpus + engine, rules, DOCX (both directions), batch, and headless GUI tests
site/                       Live Demo web page (runs the same Python engine in the browser via Pyodide)
docs/REPOSITORY_ANALYSIS.md analysis of the reference project
```

### Extending the engine
* New conjunct: add it to `CONJUNCTS` in `core/conversion_rules.py`, then add a corpus line in `tests/corpus.py`.
* House-style exceptions: use **Settings → Correction rules** (no code needed). Rules are stored in `%APPDATA%\TIS Bangla Word Converter\correction_rules.json`.
* Developer and organisation details in About are editable in **Settings → Developer info**, or in `config/settings.py`.

### Data locations
`%APPDATA%\TIS Bangla Word Converter\` holds `settings.json`, `history.sqlite3`, `autosave_input.txt`, `correction_rules.json`, and `tis.log`. In portable mode these go in `TIS_data\` next to the EXE.

---


## Developer

<a id="developer"></a>
<img src="assets/images/developer.jpg" width="110" align="left" alt="Tariqul Islam (Sumon)" style="margin-right:16px">

**তারিকুল ইসলাম (সুমন)**<br>
Msc Mathematics<br>
YouTube Channel: **TIS Academy**

- YouTube: <https://www.youtube.com/@tis.academy24>
- Facebook: <https://www.facebook.com/tariqul.islam.422531/>
- WhatsApp: <https://wa.me/8801755489719>
- GitHub: <https://github.com/tariqulislam4015>
- LinkedIn: <https://www.linkedin.com/in/tariqul3315/>

<br clear="left">

## Credits and licence

- MIT License © 2026 Tariqul Islam (Sumon) — TIS Academy. See `LICENSE`.
- Built with Python, Qt for Python (PySide6, LGPLv3), python-docx (MIT) and lxml (BSD). The Live Demo uses Pyodide (MPL-2.0).
- The open-source project **WordBuddy** by Farias Hamid Jim was studied as a reference (see `docs/REPOSITORY_ANALYSIS.md`). That repository has no licence, so none of its code is used. TIS's engine is an independent implementation.
- SutonnyMJ and Bijoy are trademarks of their respective owners. The font is not distributed.
