# Version History

Current version: **v3.04.03**

## Version Numbering Rules

| Position | Meaning | Trigger Condition |
|---|---|---|
| Last two digits (revision number) | Minor update | Bug fixes, copy changes, single-point UX improvements; increment by +1 each time, e.g. `v3.01.01 → v3.01.02` |
| Middle two digits (minor version) | Notable feature difference | Adding a new class of capability or changing usage; **confirm with the user before upgrading**, e.g. `v3.01.xx → v3.02.00` |
| First digit (major version) | Major update | Architecture or product-form-level change; suggestions may be made, decision is up to the user, e.g. `v3.xx.xx → v4.0.0` |

The update log inside the UI shows only the version number and content, not the date; this document retains dates for traceability.

---

## v3.04.03 (2026-11-24)

- Added a root-level `LICENSE` file with the standard MIT License text (Copyright (c) 2026 KylinFPV).
- Placed the same file in the development and release folders so GitHub can detect the license by filename.

## v3.04.02 (2026-11-24)

- Added a license line at the bottom of the page: the project is released under the MIT License, free forever to use, modify and distribute.
- Added section 9 "License" to the Help dialog in both Chinese and English; updated the help count from 8 to 9 sections.
- Added MIT license terms to both README versions (retain copyright and license notices; software provided as-is without warranty).

## v3.04.01ui (2026-11-23)

- Swapped the first two table columns: Analyze on the left, Rename on the right.
- De-emphasized frame analysis / tagging as a support area (light gray panel); added a prominent "Rename - final step" section visually separated from it.
- Added a hint next to "Rename files": checked files will have their selected tags written into the filenames.
- Reworked the top intro into sentence-by-sentence bilingual pairs: each Chinese sentence is followed by its full English translation. Help dialog column notes updated to match the new order.
- Fixed a misleading launcher warning: when Pillow + imageio-ffmpeg are not both installed, it no longer claims frame analysis is disabled. It now states the real requirements and gives `python -m pip install imageio-ffmpeg` as the fix.

## v3.04.01 (2026-11-23)

- Fixed the "double-click the .bat and the window flashes then closes" issue: the launcher was LF-only, so cmd.exe parsed `rem` comment words as commands and exited immediately. Converted to CRLF line endings.
- Added `.gitattributes` to lock `*.bat` to CRLF, preventing a regression to LF on commit / checkout.
- Added a smoke test asserting the launcher is CRLF with no BOM and that `.gitattributes` contains `*.bat text eol=crlf`.

## v3.04.00 (2026-11-23)

- Added a prominent Language switch in the header: Chinese is the default; when enabled, all Chinese text remains and English translation is appended below in smaller type. The choice is stored in browser localStorage.
- Made `KylinFPV` a clickable link to <https://space.bilibili.com/36780014>; supported devices are shown in bold teal / blue / orange in the header and Help dialog to distinguish camera metadata, SRT subtitles, and no-color-metadata models.
- Added "FFmpeg required" to the frame analysis panel title; moved the tagging section above the rename section; added the workflow diagram "Select analysis scope > Analyze > Tag > Select rename scope > Rename by tag" to the UI, README and Help dialog.
- Renamed `启动.bat` to `启动start.bat`; every console message now shows Chinese and English; the script uses UTF-8 without BOM plus `chcp 65001`.
- The package now ships with a default `depend/` folder and `depend/readme_depend.md` explaining exactly where Python, Pillow and ffmpeg go and how to verify them; README adds a tip for having AI complete the setup.

## v3.03.00 (2026-11-23)

- Built-in folder browser: when there is no previous location, the drive root directory is shown by default; after selecting or scanning, the last directory is remembered and opened directly next time; a successful selection via the system dialog is also synced to memory
- Removed the yellow "color mode could not be recognized..." hint module so it no longer occupies the results area; the entire frame analysis is merged into the result card, reducing card spacing
- Changed "Checked analysis files marked as + Confirm mark" into a prominent blue emphasis row, with enlarged and bolded dropdown, button, and status text
- Added support for a portable (green) dependency directory: `启动.bat` first looks for `depend\python\python.exe` and `depend\python\Scripts\python.exe`; `analyzer.py` looks for `depend\ffmpeg.exe` and `depend\bin\ffmpeg.exe`
- Rewrote README into an end-user version: opening feature overview, first chapter covers only four safety points and recommends handing the extracted package to AI for verification, second chapter gives official downloads for Python / Pillow / ffmpeg and a `depend\` directory placement example
- Extended smoke tests to 20 items, covering browser memory, layout changes, dependency directory, README simplification, and version consistency; the backend ffmpeg default was not changed

## v3.02.03 (2026-11-23)

- UI review implemented: heading font size and open-source info line, single legend, button/form focus states and contrast, card corners and light shadows, table hover and tabular numbers, narrow-screen responsiveness; the page itself does not scroll horizontally, tables scroll only within their container, with zero feature removal
- Changed the frame analysis hardware-decoding switch to a prominent bar enabled by default (GPU first, automatic fallback to CPU on failure); under `<label class="hw-bar">`, `#anHw` comes first and `.hw-state` after, both direct children, and the status pill is derived by a CSS sibling selector into "Enabled · GPU first" / "Disabled · CPU decoding", with no second JS state source added; the backend default remains CPU, and the default parameters of `analyzer.py` / `app.py` were not changed
- Unified global focus to `outline:2px solid var(--accent);outline-offset:2px`, with only `#anHw:focus-visible` overriding the local semantic color, and removed the `.hw-bar:focus-within` box-shadow double ring
- Added a "? Instructions" dialog (8 sections: disclaimer / sources / mark comparison / getting started / column descriptions / frame analysis / batch and keyboard / FAQ), mutually exclusive with the update log and built-in browser; the ESC close priority is instructions → update log → built-in browser, and the system dialog does not trigger cancel
- Added README.md: each of the four safety and privacy statements gives a "statement + source-code basis + boundary", plus dependency and directory placement, quick start, mark comparison, frame analysis, batch and undo, FAQ, and development and versioning
- Accessibility completed: version number can be triggered by keyboard, filename `span.fn` supports Enter / Space to open, dialog focus moves to the close button and is restored after closing; `prefers-reduced-motion` removes animations
- Visible copy no longer contains the historical default wording "disabled by default / not enabled by default"; historical entries retain the original text, and only the named default-value copy was changed to "manual activation required in the initial version"

## v3.02.01 (2026-11-23)

- Added a "Select first 100 unrenamed + unrecognized" button to frame analysis: first clears the current analysis selection, then selects the first 100 unrenamed and unrecognized files in table order; when the single-operation limit is exceeded, a batch prompt is shown
- Added a "Checked analysis files marked as" dropdown and a "Confirm mark" button to frame analysis: batch-changes "marked as" according to the current analysis selection, updating only the preview, not auto-renaming
- Added `tests/test_ui_batch_controls.py` smoke test: covers control presence, the first-100 selection logic, the batch-marking chain, and JS syntax
- Corrected the console startup banner version number: originally hardcoded as `v6`, changed to the current version `v3.02.01` consistent with the UI

## v3.02.00 (2026-11-23)

- Added an "Enable hardware decoding" switch (disabled by default) to the frame saturation / contrast analysis: when checked, ffmpeg `-hwaccel auto` is used to attempt GPU decoding; when the current GPU / driver / encoder does not support it, it automatically falls back to CPU
- Added a decoding-method indicator (CPU / GPU / partial fallback) to analysis results, and the run log shows the method actually used; only the frame-extraction decoding path was changed, not the decision thresholds, nor the material content / metadata / timestamps
- Added `tests/test_analyzer_hwaccel.py`: covers the default CPU, `-hwaccel auto`, failure fallback, and result indicators; end-to-end verification with real footage and `/api/analyze` passed

## v3.01.02 (2026-11-13)

- Cross-machine migration: removed machine-specific absolute paths, so the entire project can be copied to any path and run
- Launcher: uses the `DJI_PYTHON` environment variable → the current user's WorkBuddy default venv → the project's `.venv`/`venv` → `python` on PATH → `py -3`; an interpreter with Pillow + imageio-ffmpeg is preferred, and when none is found it falls back to any usable Python (core scanning/renaming needs only the standard library) and prints an English prompt
- `analyzer.py`: ffmpeg lookup was changed to runtime derivation; supports `DJI_FFMPEG`, `DJI_FFMPEG_EXTRA`, project-local `bin/ffmpeg*.exe`, with fallback derived from the current user's home directory
- QA final revisions: the launcher performs another dependency check after the interpreter is selected, and still prints a Warning when an explicit `DJI_PYTHON` points to an interpreter without dependencies; `analyzer.py`'s venv fallback scans the `ffmpeg*.exe` wildcard instead of a fixed versioned name

## v3.01.01

- Added a clickable version number and update-log entry to the header
- Established the version history and requirement list
- HLG encoding-layer forensics: HLG files from P3 / P4P write `BT.2020 / ARIB-STD-B67 / BT.2020-NCL` in the `colr` box, so HLG can be determined automatically; D-Log M / Normal / D-Log / D-Cinelike are still BT.709 and cannot be distinguished
- Recorded pending requirements: the browse dialog remembering the last directory, automatic HLG recognition via `colr`, etc.

## v3.01.00

- Added **D-Cinelike** (`_DC`): the O3 air unit SRT's `[color_md : d_cinelike]` can be automatically recognized
- Added **O3 air unit / Action 2** `DJI_xxxx.MP4` naming: when there is no `_D`, `_DN` / `_DC` is appended, with companion `.LRF/.SRT` files synced
- Added **device name display**: reads `©too` metadata (DJI Action 2, Osmo Pocket 4P/3, Osmo Nano, Avata 2, O4 Air Unit Pro, Osmo 360 II)
- File column shows `.../subfolder`; frame analysis results are filled directly into the corresponding file row
- Frame analysis is open to all files (including recognized color spaces), still requiring manual triggering by default
- Added four range checkboxes (all renamed / unrenamed / unrecognized / customized); "Undo rename" operates on the checked range, and partial undo retains the remaining records
- Marked files can be checked again for renaming, unchecked by default
- Clicking a filename opens it with the system default program
- System dialog anti-freeze: removed hidden-window parameters, added a 120-second timeout guard, and added a cancel entry

## v3.0.0

- Scan performance optimization: chunked reading of `moov`, directory-indexed replacement of O(N²) enumeration, SRT byte-level regex; about 1.7× faster on real footage
- Added saturation / contrast frame analysis (disabled by default, frames are extracted on demand after the user checks it)
- Maintained read-only recognition and idempotent renaming

## v2.0.0

Device coverage expanded from a single model to multiple models, with companion-file synchronized renaming, a built-in folder browser, and undo capability.

| Device | Color mode source | Automatic recognition |
|---|---|---|
| DJI Osmo Pocket 4P | Camera-body `ColorGammaSxS` (D-Log / D-Log 2 / Rec.2100 HLG / Rec.709) | ✅ |
| DJI Avata 360 | `.SRT` `color_md` (including `.OSV` panorama) | ✅ |
| DJI Avata 2 | `.SRT` `color_md` | ✅ (video subtitles must be enabled) |
| DJI O4 Air Unit Pro | `.SRT` `color_md` | ✅ (video subtitles must be enabled) |
| DJI Osmo 360 II | No color metadata in file (`.OSV`) | ❌ manual designation / frame reference |
| DJI Osmo Nano | No color metadata in file | ❌ manual designation / frame reference |
| DJI Osmo Pocket 3 | No color metadata in file | ❌ manual designation / frame reference |

## v1.0.0

- Basic capability: recognize the color space and rename the `_D` suffix at the end of the filename to `_D1` / `_D2` / `_DH` / `_DN` / `_DU`
- Rename only, without changing file content, metadata, or timestamps
