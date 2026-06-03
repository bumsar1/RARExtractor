#!/usr/bin/env python3
"""RAR Extractor — macOS drag & drop RAR extractor"""

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path


# ── Dependency setup (runs before the main app) ───────────────────────────────

BG_S   = "#1c1c1e"
FG_S   = "#ebebf5"
DIM_S  = "#8e8e93"
OK_S   = "#30d158"
ERR_S  = "#ff453a"
BTN_S  = "#0a84ff"
FONT_S = "Helvetica"


def _has_brew():
    return bool(shutil.which("brew") or
                Path("/opt/homebrew/bin/brew").exists() or
                Path("/usr/local/bin/brew").exists())


def _missing_deps():
    missing = {}
    if not (shutil.which("unar") or Path("/opt/homebrew/bin/unar").exists()):
        missing["unar"] = "brew"
    try:
        import tkinterdnd2  # noqa: F401
    except ImportError:
        missing["tkinterdnd2"] = "pip"
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing["Pillow"] = "pip"
    return missing


class SetupWindow:
    """First-run installer shown when dependencies are missing."""

    def __init__(self, missing: dict):
        self.missing = missing
        self.root = tk.Tk()
        self.root.title("RAR Extractor — Setup")
        self.root.geometry("480x380")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_S)
        self._build()

    def _build(self):
        tk.Label(self.root, text="Welcome to RAR Extractor",
                 font=(FONT_S, 16, "bold"), bg=BG_S, fg=FG_S).pack(pady=(24, 4))
        tk.Label(self.root,
                 text="A few tools need to be installed before you can use the app.",
                 font=(FONT_S, 12), bg=BG_S, fg=DIM_S, wraplength=400).pack(pady=(0, 16))

        # Missing items list
        for name, kind in self.missing.items():
            row = tk.Frame(self.root, bg="#2c2c2e", pady=6)
            row.pack(fill="x", padx=24, pady=3)
            icon = "🍺" if kind == "brew" else "🐍"
            tk.Label(row, text=f"  {icon}  {name}",
                     font=(FONT_S, 12), bg="#2c2c2e", fg=FG_S,
                     anchor="w").pack(side="left", padx=8)
            tk.Label(row, text=f"{'brew install' if kind == 'brew' else 'pip install'} {name}  ",
                     font=("Menlo", 11), bg="#2c2c2e", fg=DIM_S,
                     anchor="e").pack(side="right")

        # Output log
        self.log = tk.Text(self.root, height=6, bg="#2c2c2e", fg=FG_S,
                           font=("Menlo", 10), relief="flat",
                           state="disabled", wrap="word")
        self.log.pack(fill="x", padx=24, pady=(14, 0))

        # Buttons
        bar = tk.Frame(self.root, bg=BG_S)
        bar.pack(fill="x", padx=24, pady=12)

        self.status_lbl = tk.Label(bar, text="", font=(FONT_S, 11),
                                   bg=BG_S, fg=DIM_S, anchor="w")
        self.status_lbl.pack(side="left", expand=True, fill="x")

        self.btn = tk.Button(
            bar, text="Install automatically",
            font=(FONT_S, 13, "bold"),
            bg=BTN_S, fg="white", relief="flat",
            padx=18, pady=8, cursor="hand2",
            command=self._install,
        )
        self.btn.pack(side="right")

        if not _has_brew():
            self._set_status(
                "⚠️  Homebrew not found — click Install to set it up too", ERR_S)

    def _append_log(self, text: str):
        self.root.after(0, lambda: (
            self.log.configure(state="normal"),
            self.log.insert("end", text),
            self.log.see("end"),
            self.log.configure(state="disabled"),
        ))

    def _set_status(self, msg: str, color: str = DIM_S):
        self.root.after(0, lambda: self.status_lbl.configure(text=msg, fg=color))

    def _install(self):
        self.btn.configure(state="disabled", text="Installing …")
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")}
        ok = True

        # Install Homebrew if missing
        if not _has_brew():
            self._set_status("Installing Homebrew …", DIM_S)
            self._append_log("▶ Installing Homebrew...\n")
            r = subprocess.run(
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                shell=True, capture_output=True, text=True, env=env,
            )
            self._append_log(r.stdout[-800:] or r.stderr[-800:])
            if r.returncode != 0:
                self._set_status("Homebrew install failed — try running install.sh manually", ERR_S)
                self.root.after(0, lambda: self.btn.configure(state="normal", text="Retry"))
                return

        # brew packages
        brew_pkgs = [n for n, t in self.missing.items() if t == "brew"]
        for pkg in brew_pkgs:
            self._set_status(f"Installing {pkg} …", DIM_S)
            self._append_log(f"▶ brew install {pkg}\n")
            r = subprocess.run(["brew", "install", pkg],
                               capture_output=True, text=True, env=env)
            self._append_log(r.stdout[-400:] or r.stderr[-400:])
            if r.returncode != 0:
                ok = False
                self._append_log(f"✗ Failed to install {pkg}\n")

        # pip packages
        pip_pkgs = [n for n, t in self.missing.items() if t == "pip"]
        if pip_pkgs:
            self._set_status("Installing Python packages …", DIM_S)
            self._append_log(f"▶ pip install {' '.join(pip_pkgs)}\n")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install",
                 "--quiet", "--break-system-packages"] + pip_pkgs,
                capture_output=True, text=True, env=env,
            )
            self._append_log(r.stdout or r.stderr or "Done.\n")
            if r.returncode != 0:
                ok = False

        if ok:
            self._set_status("✓ All done! Launching app …", OK_S)
            self._append_log("\n✓ Setup complete — starting RAR Extractor\n")
            self.root.after(1200, self._restart)
        else:
            self._set_status("Some installs failed — check the log above", ERR_S)
            self.root.after(0, lambda: self.btn.configure(state="normal", text="Retry"))

    def _restart(self):
        self.root.destroy()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def run(self):
        self.root.mainloop()


def _install_quick_action():
    """Create the Finder Quick Action (Service) if not already installed."""
    service_dir = Path.home() / "Library/Services/RAR Extractor.workflow/Contents"
    if (service_dir / "document.wflow").exists():
        return  # already installed

    service_dir.mkdir(parents=True, exist_ok=True)

    (service_dir / "Info.plist").write_text("""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSServices</key>
    <array>
        <dict>
            <key>NSMenuItem</key>
            <dict><key>default</key><string>RAR Extractor</string></dict>
            <key>NSMessage</key><string>runWorkflowAsService</string>
            <key>NSSendFileTypes</key>
            <array><string>public.data</string></array>
        </dict>
    </array>
</dict>
</plist>
""")

    # Shell script used inside the workflow — finds unar regardless of install path
    shell_script = (
        'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"\n'
        'for f in "$@"; do\n'
        '    [[ "${f##*.}" != "rar" ]] && [[ "${f##*.}" != "RAR" ]] && continue\n'
        '    stem="${f%.*}"\n'
        '    mkdir -p "$stem"\n'
        '    if unar -o "$stem" -f "$f" > /tmp/rar_extractor.log 2>&1; then\n'
        '        osascript -e "display notification \\"Extracted: $(basename \\"$stem\\")/" with title \\"RAR Extractor\\" sound name \\"Glass\\""\n'
        '    else\n'
        '        err=$(tail -1 /tmp/rar_extractor.log)\n'
        '        osascript -e "display notification \\"$err\\" with title \\"RAR Extractor\\""\n'
        '    fi\n'
        'done\n'
    )

    (service_dir / "document.wflow").write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key><string>521.1</string>
    <key>AMApplicationVersion</key><string>2.10</string>
    <key>AMDocumentVersion</key><string>2</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key><string>List</string>
                    <key>Optional</key><true/>
                    <key>Types</key><array><string>com.apple.cocoa.path</string></array>
                </dict>
                <key>AMActionVersion</key><string>2.0.3</string>
                <key>AMApplication</key><array><string>Automator</string></array>
                <key>AMParameterProperties</key>
                <dict>
                    <key>COMMAND_STRING</key><dict/>
                    <key>CheckedForUserDefaultShell</key><dict/>
                    <key>inputMethod</key><dict/>
                    <key>shell</key><dict/>
                    <key>source</key><dict/>
                </dict>
                <key>AMProvides</key>
                <dict>
                    <key>Container</key><string>List</string>
                    <key>Types</key><array><string>com.apple.cocoa.path</string></array>
                </dict>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run Shell Script.action</string>
                <key>ActionName</key><string>Run Shell Script</string>
                <key>ActionParameters</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <string>{shell_script}</string>
                    <key>CheckedForUserDefaultShell</key><true/>
                    <key>inputMethod</key><integer>1</integer>
                    <key>shell</key><string>/bin/bash</string>
                    <key>source</key><string></string>
                </dict>
                <key>BundleIdentifier</key><string>com.apple.RunShellScript</string>
                <key>CFBundleVersion</key><string>2.0.3</string>
                <key>CanShowSelectedItemsWhenRun</key><false/>
                <key>CanShowWhenRun</key><true/>
                <key>Category</key><array><string>AMCategoryUtilities</string></array>
                <key>Class Name</key><string>RunShellScriptAction</string>
                <key>InputUUID</key><string>A1B2C3D4-0001-0001-0001-A1B2C3D40001</string>
                <key>Keywords</key><array><string>Shell</string></array>
                <key>OutputUUID</key><string>A1B2C3D4-0001-0001-0001-A1B2C3D40002</string>
                <key>UUID</key><string>A1B2C3D4-0001-0001-0001-A1B2C3D40003</string>
                <key>UnlocalizedApplications</key><array><string>Automator</string></array>
                <key>arguments</key>
                <dict>
                    <key>0</key>
                    <dict>
                        <key>default value</key><integer>0</integer>
                        <key>name</key><string>inputMethod</string>
                        <key>required</key><string>0</string>
                        <key>type</key><string>0</string>
                        <key>uuid</key><string>0</string>
                    </dict>
                </dict>
                <key>isViewVisible</key><integer>1</integer>
                <key>location</key><string>309.000000:253.000000</string>
                <key>nibPath</key>
                <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
            </dict>
            <key>isViewVisible</key><integer>1</integer>
        </dict>
    </array>
    <key>connectors</key><dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>serviceInputTypeIdentifier</key>
        <string>com.apple.Automator.fileSystemObject</string>
        <key>serviceOutputTypeIdentifier</key>
        <string>com.apple.Automator.nothing</string>
        <key>serviceProcessesInput</key><integer>0</integer>
        <key>systemImageName</key><string>NSActionTemplate</string>
        <key>workflowTypeIdentifier</key>
        <string>com.apple.Automator.servicesMenu</string>
    </dict>
</dict>
</plist>
""")

    # Reload the services database
    subprocess.run(["/System/Library/CoreServices/pbs", "-update"],
                   capture_output=True)


def run_setup_if_needed():
    missing = _missing_deps()
    if missing:
        SetupWindow(missing).run()
    _install_quick_action()


# ── Main app imports (safe after setup) ───────────────────────────────────────

import json  # noqa: E402
import queue  # noqa: E402
from tkinter import filedialog, simpledialog  # noqa: E402

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

BG       = "#1c1c1e"
ZONE_BG  = "#2c2c2e"
ZONE_HI  = "#3a3a3c"
FG       = "#ebebf5"
DIM      = "#8e8e93"
OK_CLR   = "#30d158"
ERR_CLR  = "#ff453a"
BTN_CLR  = "#0a84ff"
BTN2_CLR = "#3a3a3c"
FONT     = "Helvetica"


# ── Core logic ────────────────────────────────────────────────────────────────

def find_tool():
    for tool in ["unar", "7zz", "7z", "unrar"]:
        try:
            subprocess.run([tool, "--help"], capture_output=True, timeout=2)
            return tool
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def list_archive(path: Path):
    try:
        r = subprocess.run(["lsar", "-j", str(path)],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return json.loads(r.stdout).get("lsarContents", [])
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return None


def fmt_size(n):
    if not n:        return "—"
    if n < 1024:     return f"{n} B"
    if n < 1024**2:  return f"{n/1024:.1f} KB"
    return f"{n/1024**2:.1f} MB"


def _needs_password(output: str) -> bool:
    low = output.lower()
    return any(w in low for w in ["password", "encrypted", "passphrase", "wrong password"])


def extract_rar(path: Path, password: str | None = None):
    """Returns (success, message, needs_password, output_dir)."""
    output_dir = path.parent / path.stem
    output_dir.mkdir(exist_ok=True)

    tool = find_tool()
    if not tool:
        return False, "unar not found — run: brew install unar", False, None

    if tool == "unar":
        cmd = ["unar", "-o", str(output_dir), "-f", str(path)]
        if password:
            cmd = ["unar", "-p", password, "-o", str(output_dir), "-f", str(path)]
    elif tool == "unrar":
        cmd = ["unrar", "x", "-y"] + ([f"-p{password}"] if password else []) + [str(path), str(output_dir) + "/"]
    else:
        cmd = [tool, "x", str(path), f"-o{output_dir}", "-y"] + ([f"-p{password}"] if password else [])

    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stderr + r.stdout

    if r.returncode == 0:
        return True, f"→ {output_dir.name}/", False, output_dir

    return False, out.strip()[:120], _needs_password(out), None


# ── App ───────────────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.root.title("RAR Extractor")
        self.root.geometry("560x520")
        self.root.minsize(420, 360)
        self.root.configure(bg=BG)

        self._queue: dict[Path, str] = {}        # path → tree iid
        self._extracted: dict[Path, Path] = {}   # path → output_dir (successful only)
        self._lock = threading.Lock()
        self._pw_queue: queue.Queue = queue.Queue()

        self._apply_styles()
        self._build()

        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>",      self._on_drop)
            self.root.dnd_bind("<<DragEnter>>", lambda e: self._highlight(True))
            self.root.dnd_bind("<<DragLeave>>", lambda e: self._highlight(False))

        # Handle "Open With" Apple Events from Finder
        try:
            self.root.createcommand("::tk::mac::OpenDocument", self._open_document)
        except Exception:
            pass

        # Handle files passed as command-line arguments (open from terminal or script)
        if len(sys.argv) > 1:
            rars = [Path(p) for p in sys.argv[1:]
                    if Path(p).suffix.lower() == ".rar" and Path(p).exists()]
            if rars:
                self.root.after(200, lambda: self._add_files(rars))

    # ── Styles ────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style(self.root)
        s.theme_use("default")
        s.configure("T.Treeview",
                     background=ZONE_BG, foreground=FG,
                     fieldbackground=ZONE_BG, borderwidth=0,
                     rowheight=24, font=(FONT, 12))
        s.configure("T.Treeview.Heading",
                     background=ZONE_HI, foreground=DIM,
                     relief="flat", font=(FONT, 11))
        s.map("T.Treeview.Heading",
              background=[("active", ZONE_HI), ("pressed", ZONE_HI)],
              foreground=[("active", DIM),     ("pressed", DIM)],
              relief=[("active", "flat"),      ("pressed", "flat")])
        s.map("T.Treeview",
              background=[("selected", BTN_CLR)],
              foreground=[("selected", "white")])
        s.configure("Primary.TButton",
                     background=BTN_CLR, foreground="white",
                     font=(FONT, 13, "bold"), relief="flat", padding=(20, 9))
        s.map("Primary.TButton",
              background=[("active", "#0070d6"), ("disabled", ZONE_HI)],
              foreground=[("disabled", DIM)])
        s.configure("Secondary.TButton",
                     background=BTN2_CLR, foreground=FG,
                     font=(FONT, 12), relief="flat", padding=(14, 9))
        s.map("Secondary.TButton",
              background=[("active", "#4a4a4e"), ("disabled", "#2a2a2c")],
              foreground=[("disabled", DIM)])

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self):
        # Logo header
        logo_path = Path(__file__).parent / "logo.png"
        self._logo_img = None
        if logo_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(str(logo_path)).convert("RGBA")
                # Remove black/near-black background
                try:
                    import numpy as np
                    arr = np.array(img)
                    mask = (arr[:,:,0] < 30) & (arr[:,:,1] < 30) & (arr[:,:,2] < 30)
                    arr[mask, 3] = 0
                    img = Image.fromarray(arr)
                except ImportError:
                    data = [(r, g, b, 0) if r < 30 and g < 30 and b < 30 else (r, g, b, a)
                            for r, g, b, a in img.getdata()]
                    img.putdata(data)
                img = img.resize((110, 110), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(self.root, image=self._logo_img,
                         bg=BG, pady=10).pack()
            except Exception:
                pass

        # Drop zone
        self.zone = tk.Label(
            self.root,
            text="Drop RAR files here  —  or click to browse",
            font=(FONT, 13), bg=ZONE_BG, fg=DIM,
            cursor="hand2", pady=16,
        )
        self.zone.pack(fill="x", padx=14, pady=(0, 8))
        self.zone.bind("<Button-1>", self._browse)

        # Treeview
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True, padx=14)

        self.tree = ttk.Treeview(
            frame, style="T.Treeview",
            columns=("right",), show="tree headings", selectmode="none",
        )
        self.tree.heading("#0",    text="Name",  anchor="w")
        self.tree.heading("right", text="",      anchor="e")
        self.tree.column("#0",    stretch=True, minwidth=200)
        self.tree.column("right", width=140, anchor="e", stretch=False)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Bottom bar
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=14, pady=10)

        self.status_lbl = tk.Label(
            bar, text="Ready" if find_tool() else "⚠️  brew install unar",
            font=(FONT, 11), bg=BG,
            fg=DIM if find_tool() else ERR_CLR,
            anchor="w", wraplength=220,
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)

        self.reveal_btn = ttk.Button(
            bar, text="Reveal in Finder", style="Secondary.TButton",
            state="disabled", command=self._reveal_all,
        )
        self.reveal_btn.pack(side="right", padx=(6, 0))

        self.clear_btn = ttk.Button(
            bar, text="Clear", style="Secondary.TButton",
            state="disabled", command=self._clear_queue,
        )
        self.clear_btn.pack(side="right", padx=(6, 0))

        self.extract_btn = ttk.Button(
            bar, text="Extract", style="Primary.TButton",
            state="disabled", command=self._extract_all,
        )
        self.extract_btn.pack(side="right")

    # ── Open With / Apple Events ──────────────────────────────────────────

    def _open_document(self, *args):
        """Called by macOS when files are opened via 'Open With' in Finder."""
        rars = [Path(p) for p in args if Path(p).suffix.lower() == ".rar" and Path(p).exists()]
        if rars:
            self.root.lift()
            self.root.focus_force()
            self._add_files(rars)

    # ── Drag & browse ─────────────────────────────────────────────────────

    def _highlight(self, on: bool):
        self.zone.configure(bg=ZONE_HI if on else ZONE_BG)

    def _on_drop(self, event):
        self._highlight(False)
        paths = [Path(f.strip("{}")) for f in self.root.tk.splitlist(event.data)]
        rars  = [p for p in paths if p.suffix.lower() == ".rar" and p.exists()]
        if rars:
            self._add_files(rars)

    def _browse(self, _=None):
        files = filedialog.askopenfilenames(
            title="Select RAR files",
            filetypes=[("RAR files", "*.rar *.RAR"), ("All files", "*.*")],
        )
        if files:
            self._add_files([Path(f) for f in files])

    # ── Queue ─────────────────────────────────────────────────────────────

    def _add_files(self, paths: list[Path]):
        new = [p for p in paths if p not in self._queue]
        if not new:
            return
        for path in new:
            iid = self.tree.insert("", "end",
                                   text=f"📦  {path.name}",
                                   values=("Reading …",), open=False)
            self._queue[path] = iid
        self._refresh_buttons()
        for path in new:
            threading.Thread(target=self._load_entries, args=(path,), daemon=True).start()

    def _clear_queue(self):
        self._queue.clear()
        self._extracted.clear()
        self.tree.delete(*self.tree.get_children())
        self._refresh_buttons()
        self._set_status("Ready", DIM)

    def _load_entries(self, path: Path):
        entries = list_archive(path)
        self.root.after(0, lambda: self._populate_path(path, entries))

    def _populate_path(self, path: Path, entries):
        iid = self._queue.get(path)
        if iid is None:
            return
        for child in self.tree.get_children(iid):
            self.tree.delete(child)
        if entries is None:
            self.tree.item(iid, values=("Could not read archive",))
            return

        dir_nodes: dict[str, str] = {}

        def ensure_dir(parts: list[str]) -> str:
            if not parts:
                return iid
            key = "/".join(parts)
            if key in dir_nodes:
                return dir_nodes[key]
            parent = ensure_dir(parts[:-1])
            node = self.tree.insert(parent, "end",
                                    text=f"📁  {parts[-1]}", values=("",), open=False)
            dir_nodes[key] = node
            return node

        file_count = 0
        for entry in entries:
            name: str = entry.get("XADFileName", "")
            is_dir    = entry.get("XADIsDirectory", False)
            size: int = entry.get("XADFileSize", 0)
            parts = [p for p in name.strip("/").split("/") if p]
            if not parts:
                continue
            if is_dir:
                ensure_dir(parts)
            else:
                parent = ensure_dir(parts[:-1])
                self.tree.insert(parent, "end",
                                 text=f"📄  {parts[-1]}", values=(fmt_size(size),))
                file_count += 1

        noun = "file" if file_count == 1 else "files"
        self.tree.item(iid, values=(f"{file_count} {noun}",), open=True)
        self._refresh_buttons()

    # ── Extract ───────────────────────────────────────────────────────────

    def _extract_all(self):
        paths = list(self._queue.keys())
        if not paths:
            return
        self.extract_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        n = len(paths)
        self._set_status(f"Extracting {n} {'files' if n > 1 else 'file'} …", DIM)

        done = {"n": 0, "ok": 0}

        def run(path: Path):
            iid = self._queue.get(path)
            if iid:
                self.root.after(0, lambda i=iid: self.tree.item(i, values=("⏳ Extracting …",)))

            ok, msg, needs_pw, out_dir = extract_rar(path)

            # Password retry
            if not ok and needs_pw:
                pwd = self._ask_password(path.name)
                if pwd:
                    ok, msg, _, out_dir = extract_rar(path, password=pwd)

            if iid:
                label = f"✓  {msg}" if ok else f"✗  {msg}"
                self.root.after(0, lambda i=iid, l=label: self.tree.item(i, values=(l,)))

            if ok and out_dir:
                with self._lock:
                    self._extracted[path] = out_dir

            with self._lock:
                done["n"] += 1
                if ok:
                    done["ok"] += 1
                if done["n"] == len(paths):
                    self.root.after(0, lambda: self._on_all_done(done["ok"], len(paths)))

        for p in paths:
            threading.Thread(target=run, args=(p,), daemon=True).start()

    def _on_all_done(self, ok: int, total: int):
        if ok == total:
            self._set_status(f"✓  {ok} {'files' if ok > 1 else 'file'} extracted", OK_CLR)
        else:
            self._set_status(f"✓ {ok} extracted  ✗ {total - ok} failed", ERR_CLR)
        self._refresh_buttons()

    # ── Password ──────────────────────────────────────────────────────────

    def _ask_password(self, filename: str) -> str | None:
        """Ask for a password on the main thread and return it."""
        self.root.after(0, lambda: self._pw_queue.put(
            simpledialog.askstring(
                "Password required",
                f"Enter password for:\n{filename}",
                show="*",
                parent=self.root,
            )
        ))
        return self._pw_queue.get()

    # ── Reveal in Finder ──────────────────────────────────────────────────

    def _reveal_all(self):
        for out_dir in self._extracted.values():
            if out_dir.exists():
                subprocess.Popen(["open", str(out_dir)])

    def _on_tree_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or self.tree.parent(iid):
            return  # only top-level rows
        for path, row_iid in self._queue.items():
            if row_iid == iid and path in self._extracted:
                out_dir = self._extracted[path]
                if out_dir.exists():
                    subprocess.Popen(["open", str(out_dir)])

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_buttons(self):
        n = len(self._queue)
        has_extracted = bool(self._extracted)

        # Extract button
        if n == 0:
            self.extract_btn.configure(state="disabled", text="Extract")
        else:
            label = f"Extract  ({n})" if n > 1 else "Extract"
            ready = any(
                self.tree.item(iid, "values") not in [("Reading …",), ()]
                for iid in self._queue.values()
            )
            self.extract_btn.configure(text=label,
                                       state="normal" if ready else "disabled")

        # Clear button
        self.clear_btn.configure(state="normal" if n > 0 else "disabled")

        # Reveal button
        self.reveal_btn.configure(state="normal" if has_extracted else "disabled")

    def _set_status(self, msg: str, color: str = DIM):
        self.root.after(0, lambda: self.status_lbl.configure(text=msg, fg=color))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    run_setup_if_needed()
    App().run()
