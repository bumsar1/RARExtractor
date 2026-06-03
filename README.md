# RAR Extractor

A simple macOS drag-and-drop app for extracting RAR files. Drop one or more archives onto the window, preview their contents, and extract them all in parallel with a single click.

![macOS](https://img.shields.io/badge/macOS-12%2B-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

## Features

- Drag & drop one or multiple RAR files at once
- Preview archive contents (files and folders) before extracting
- Parallel extraction — all archives extracted simultaneously
- Extracts into a folder next to the original file
- Finder right-click integration via a Quick Action (Services menu)
- Dark mode UI

## Requirements

- macOS 12 or later
- [Homebrew](https://brew.sh)
- Python 3.10+

## Install

```bash
git clone https://github.com/bumsar1/RARExtractor.git
cd RARExtractor
./install.sh
```

The install script will:
1. Install `unar` via Homebrew (the extraction engine)
2. Install the `tkinterdnd2` Python package
3. Build `RAR Extractor.app` in the `RARExtractor` folder
4. Install a Finder Quick Action (right-click → Services → RAR Extractor)

## Usage

**Drag & drop app** — open `RAR Extractor.app`, drop RAR files into the window, and click **Extract**.

**Right-click** — right-click any `.rar` file in Finder → Services → **RAR Extractor**. The archive is extracted silently and a notification appears when done.

## How extraction works

Each archive is extracted into a new folder placed next to the original file:

```
Downloads/
  archive.rar
  archive/        ← extracted here
    file1.txt
    file2.png
```
