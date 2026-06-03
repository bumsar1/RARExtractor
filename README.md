# RAR Extractor

<p align="center">
  <img src="logo.png" width="160" alt="RAR Extractor logo">
</p>

<p align="center">
  A simple macOS drag-and-drop app for extracting RAR files.
</p>

<p align="center">
  <a href="https://github.com/bumsar1/RARExtractor/releases/latest">
    <img src="https://img.shields.io/github/v/release/bumsar1/RARExtractor?label=Download&style=for-the-badge&color=7c3aed" alt="Download">
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/macOS-12%2B-black?style=for-the-badge" alt="macOS">
  &nbsp;
  <img src="https://img.shields.io/badge/Python-3.10%2B-black?style=for-the-badge" alt="Python">
</p>

---

## Install

1. Download **[RAR_Extractor.dmg](https://github.com/bumsar1/RARExtractor/releases/latest)** from the latest release
2. Open the DMG and drag **RAR Extractor** into your Applications folder
3. Launch the app — it will install any missing dependencies automatically on first run

> **First launch:** A setup window appears if anything is missing (unar, Python packages). Click **Install automatically** and the app handles the rest — no Terminal needed.

---

## Features

- **Drag & drop** — drop one or multiple RAR files at once
- **Preview** — see the full file tree inside each archive before extracting
- **Parallel extraction** — all archives extracted simultaneously
- **Password support** — detects encrypted RARs and prompts for the password
- **Reveal in Finder** — opens the extracted folder when done (or double-click a row)
- **Clear queue** — remove all archives and start over
- **Right-click integration** — right-click any `.rar` file in Finder → Services → **RAR Extractor**
- **Dark mode UI**

---

## How it works

Each archive is extracted into a new folder placed next to the original file:

```
Downloads/
  archive.rar
  archive/        ← extracted here
    file1.txt
    file2.png
```

---

## Requirements

- macOS 12 or later
- Python 3.10+
- [Homebrew](https://brew.sh) (installed automatically if missing)
