# Phase 1 — Analysis of the reference repository `fariasjim/word_buddy`

Analyzed commit: `dfc23c8` ("Update README.md"), cloned 2026-11-21.

## 1. What the project is

WordBuddy is a Tkinter/CustomTkinter desktop tool by Farias Hamid Jim. Its main features are:

1. Unicode Bengali → Bijoy (SutonnyMJ) conversion of `.docx` files.
2. Bengali → English MCQ translation through the Google Translate web service.

It also has a GitHub-based self-updater and a PyQt6 splash screen. The README warns that the project is still in progress and that some functions may not work.

## 2. Source file structure

| File | Role |
|---|---|
| `Wdb.py` | Entry point. PyQt6 animated-GIF splash screen. Calls the GitHub API **at import time** (`requests.get(url)` at module level) to check `version.txt`, then imports `Main`. |
| `Main.py` | CustomTkinter GUI: tabs for converter and translator, file pickers, "overwrite", "highlight", and "open after" checkboxes. Also contains code that copies the script into a writable `PATH` folder and runs `setx PATH` when started as admin. |
| `convertion_logic.py` | DOCX traversal, calls to `converter.Unicode().convertUnicodeToBijoy`, a `minor_replacement_map` of post-fixes, and setting the SutonnyMJ font on runs. |
| `converter.py` | The conversion engine. A Python port of the widely circulated JavaScript "Unicode → Bijoy" routine: a `main_char` dict plus two reordering passes. |
| `util.py` | PHP/JS-style helpers (`mb_strlen`, `mbCharAt`, `preg_replace`) that `converter.py` uses. |
| `wordconv.py` | An older stand-alone script version of the converter, which only converts runs whose font is exactly "SolaimanLipi". |
| `translation_logic.py`, `translator.py` | MCQ translation through `deep_translator.GoogleTranslator` and `docxlatex`. |
| `auth.py`, `auth_panel.py`, `devinfo.py`, `web_bridge.py`, `index.html` | Login panel, developer-info window, a web-bridge experiment. |
| `update.bat`, `repo_update.bat` | Updater scripts that download the repo ZIP and overwrite files. |
| `*.spec`, `assets/BuildCode.txt` | PyInstaller one-file builds. |
| `TestCases/`, `testcase1.docx`, `new.docx`, … | Sample documents. These are not automated tests. |

## 3. Conversion algorithm (as implemented)

`convertUnicodeToBijoy(src)`:

1. **Prefix hack**: prepends the literal `"কর্ড"` to the input and strips 2 output characters at the end. This works around an off-by-one in the reph logic when a reph is at index 0. It can corrupt the output when the prefix interacts with the first cluster.
2. Normalizes `ো`, `ৌ`, `য়` with no-op `re.sub` calls. The pattern and replacement are identical strings, so these do nothing for decomposed input.
3. `reArranceUnicodeTextForASCI`: an index-juggling loop that moves pre-base vowel signs (`ি ে ৈ`) in front of the consonant cluster, and moves `র্` (reph) to after the cluster.
4. `doCharMap`: iterates the ~200-entry `main_char` dict and runs **`re.sub` once per key over the whole string**. That means about 200 full-string regex passes, and the result depends on dict insertion order. Keys are not regex-escaped, so `"।"` and others only work by accident.
5. A loop that swaps `©` with the next character. It raises `IndexError` when `©` is the last character, which is why there is a special case that strips a trailing `©`.
6. In `convertion_logic.py`, a second dict of ~90 **output-side** string replacements (`minor_replacement_map`) is applied with one alternation regex. It fixes u-kar and ū-kar glyph variants (`Ky→Kz`, `f~→f‚`), r-fola variants, `য়ে` ordering, and others. It also contains a catch-all `"Ö":"ª"` that rewrites every r-fola glyph, and entries such as `"Zowr":"Zwor"` that are word-specific patches.
7. If the first output character is `‡` or `‰`, it is swapped to the word-initial form `†`/`ˆ`. This is only checked at index 0 of a run, not after spaces, except through the `" ‡"` minor fix.

### Mapping tables
- `main_char` (Unicode → Bijoy) has about 210 entries. Some keys are duplicated (`"্র"` appears twice with different values, so the later one silently wins).
- `conversionMap` (Bijoy → Unicode) exists but is never used. There is no reverse conversion.

## 4. DOCX handling

- Converts only `doc.paragraphs` and **top-level** `doc.tables`. It misses headers, footers, nested tables, text boxes, footnotes, content controls, and hyperlink runs (python-docx's `paragraph.runs` skips runs inside `<w:hyperlink>`).
- A run is converted only if `run.font.name` is in a hard-coded list of Unicode font names. Runs that **inherit** their font from a style or docDefaults (`run.font.name is None`, which is the most common case) are skipped, so a lot of Bengali text stays unconverted.
- Converts run by run. When a word is split across runs (spell-check `rsid` splits, partial bold), pre-base vowels and reph cannot be reordered across the boundary, which gives wrong output. The word-initial e-kar check also looks only at the run's own first character.
- Mixed Bengali/English runs are set wholesale to SutonnyMJ. English letters and ASCII digits then display as Bengali glyphs.
- Sets `w:ascii`, `w:hAnsi`, and `w:cs` to SutonnyMJ. This part is correct and worth keeping.
- Before converting, it writes `<input>.bkup` **next to the user's file**. When "overwrite" is ticked, the output path is the input path.
- The module-level list `runs = []` is never reset, so the "Total words converted" count grows with every conversion in the same session. It also counts runs, not words.

## 5. UI implementation

- CustomTkinter with a custom tab widget and an animated theme toggle.
- All work runs on the Tk main thread, so the window freezes during conversion of large files.
- Module-level globals (`file_path`, `save_path`) are shared between tabs.

## 6. Dependencies

`requirements.txt` pins PyQt6, customtkinter, python-docx, deep-translator, docxlatex, requests, and others. Two GUI toolkits (Tk and Qt) are shipped together. The README asks for "Python 3.14 minimum", which is unnecessary.

## 7. Bugs and limitations found

1. Inherited-font runs are not converted (the most impactful bug).
2. No headers, footers, nested tables, text boxes, or hyperlinks.
3. Cross-run clusters are corrupted.
4. The "কর্ড" prefix hack and the `IndexError` on a trailing reph.
5. Order-dependent multi-pass regex replacement. It is slow, O(keys × length), and fragile.
6. The `minor_replacement_map` catch-all rules (`"Ö":"ª"`, `"Ê":"Ð"`) and word-specific patches indicate the base mapping is wrong in places. They also risk rewriting legitimate sequences.
7. Duplicate dict keys.
8. No reverse conversion, even though a Bijoy→Unicode table exists.
9. Network call at import time: the app cannot start offline if `requests` raises.
10. Self-modification of `PATH` with `setx` (it truncates PATH longer than 1024 characters) and auto-update by overwriting program files.
11. The UI thread blocks during conversion.
12. No automated tests.

## 8. Licensing considerations

The repository has **no LICENSE file**, and GitHub shows no license. Under default copyright, no permission is granted to copy, modify, or redistribute its code. Therefore:

- **No code from `word_buddy` is reused in TIS.** The TIS engine (`core/`) is an independent implementation with a different design: one-pass syllable-cluster parsing, a greedy longest-match conjunct table, context-sensitive glyph-variant selection, and a reverse decoder.
- The *SutonnyMJ / Bijoy glyph encoding* (for example, that `ক` is stored as byte `0x4B` "K") is a factual property of the font's character layout, not creative expression. The tables in `core/conversion_rules.py` were written from that encoding knowledge. Where the reference repo's tables or fixes exposed a fact about the encoding (for example, that `কু` uses the `z` u-kar variant), that fact was cross-checked for consistency, but no code or table text was copied.
- The sample `.docx` files from the repo were read locally only to understand real-world input. They are **not** redistributed or bundled.
- Credit: WordBuddy is acknowledged in the About dialog and README as the analyzed reference.

## 9. Design decisions taken for TIS as a result

| Problem in reference | TIS approach |
|---|---|
| Font-name whitelist | Convert any run that contains characters in the Bengali block U+0980–U+09FF. Bijoy text never contains them, so this is unambiguous and idempotent. |
| Run-by-run conversion | Paragraph-level cluster analysis. A syllable split across runs is moved into the run where it starts (the minimum change). The previous character is passed as context for word-initial glyph forms. |
| Mixed runs set wholesale to SutonnyMJ | Mixed runs are split into Bengali and non-Bengali segments. Only the Bengali segment gets SutonnyMJ, and the other segment keeps the original formatting. English, ASCII digits, and math symbols stay readable. |
| Post-hoc string patches | Glyph variants (u-kar `y/z/–/æ`, ū-kar `~/‚/ƒ`, ri-kar `…/„`, r-fola `Ö/ª/«`, e-kar `†/‡`) are chosen while rendering, from the preceding glyph. User-defined corrections are an explicit, literal, optional layer. |
| Headers, footers, and others skipped | Every story part (body, headers, footers, footnotes, endnotes, comments), including text boxes, content controls, hyperlinks, and nested tables, is processed through XML traversal. |
| Overwrites and backup next to the user's file | Never overwrites by default. Output names are suggested (`_Unicode` → `_Bijoy`), and collisions get ` (2)` suffixes. |
| No reverse conversion | A Bijoy → Unicode decoder is provided for text mode. It is also used in tests for round-trip consistency checks. |
