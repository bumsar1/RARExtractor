#!/usr/bin/env python3
"""RAR Extractor — macOS drag & drop archive extractor"""

import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


# ── Theme ─────────────────────────────────────────────────────────────────────

BG        = "#161618"   # window background
CARD      = "#242428"   # panels / tree background
CARD_HI   = "#2f2f35"   # hover / headers
BORDER    = "#3a3a42"
FG        = "#ececf1"
DIM       = "#8e8e93"
OK_CLR    = "#30d158"
ERR_CLR   = "#ff453a"
ACCENT    = "#8b5cf6"   # logo purple
ACCENT_HI = "#7445f5"
FONT      = "Helvetica Neue"

SUPPORTED = {".rar", ".zip", ".7z"}


def is_archive(p: Path) -> bool:
    return p.suffix.lower() in SUPPORTED and p.exists()


# ── Dependency setup (runs before the main app) ───────────────────────────────

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
        self.root.configure(bg=BG)
        self._build()

    def _build(self):
        tk.Label(self.root, text="Welcome to RAR Extractor",
                 font=(FONT, 16, "bold"), bg=BG, fg=FG).pack(pady=(24, 4))
        tk.Label(self.root,
                 text="A few tools need to be installed before you can use the app.",
                 font=(FONT, 12), bg=BG, fg=DIM, wraplength=400).pack(pady=(0, 16))

        for name, kind in self.missing.items():
            row = tk.Frame(self.root, bg=CARD, pady=6)
            row.pack(fill="x", padx=24, pady=3)
            icon = "🍺" if kind == "brew" else "🐍"
            tk.Label(row, text=f"  {icon}  {name}",
                     font=(FONT, 12), bg=CARD, fg=FG,
                     anchor="w").pack(side="left", padx=8)
            tk.Label(row, text=f"{'brew install' if kind == 'brew' else 'pip install'} {name}  ",
                     font=("Menlo", 11), bg=CARD, fg=DIM,
                     anchor="e").pack(side="right")

        self.log = tk.Text(self.root, height=6, bg=CARD, fg=FG,
                           font=("Menlo", 10), relief="flat",
                           state="disabled", wrap="word")
        self.log.pack(fill="x", padx=24, pady=(14, 0))

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=24, pady=12)

        self.status_lbl = tk.Label(bar, text="", font=(FONT, 11),
                                   bg=BG, fg=DIM, anchor="w")
        self.status_lbl.pack(side="left", expand=True, fill="x")

        self.btn = tk.Button(
            bar, text="Install automatically",
            font=(FONT, 13, "bold"),
            bg=ACCENT, fg="white", relief="flat",
            padx=18, pady=8, cursor="hand2",
            command=self._install,
        )
        self.btn.pack(side="right")

        if not _has_brew():
            self._set_status(
                "⚠️  Homebrew not found — click Install to set it up too", ERR_CLR)

    def _append_log(self, text: str):
        self.root.after(0, lambda: (
            self.log.configure(state="normal"),
            self.log.insert("end", text),
            self.log.see("end"),
            self.log.configure(state="disabled"),
        ))

    def _set_status(self, msg: str, color: str = DIM):
        self.root.after(0, lambda: self.status_lbl.configure(text=msg, fg=color))

    def _install(self):
        self.btn.configure(state="disabled", text="Installing …")
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")}
        ok = True

        if not _has_brew():
            self._set_status("Installing Homebrew …", DIM)
            self._append_log("▶ Installing Homebrew...\n")
            r = subprocess.run(
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                shell=True, capture_output=True, text=True, env=env,
            )
            self._append_log(r.stdout[-800:] or r.stderr[-800:])
            if r.returncode != 0:
                self._set_status("Homebrew install failed — try running install.sh manually", ERR_CLR)
                self.root.after(0, lambda: self.btn.configure(state="normal", text="Retry"))
                return

        brew_pkgs = [n for n, t in self.missing.items() if t == "brew"]
        for pkg in brew_pkgs:
            self._set_status(f"Installing {pkg} …", DIM)
            self._append_log(f"▶ brew install {pkg}\n")
            r = subprocess.run(["brew", "install", pkg],
                               capture_output=True, text=True, env=env)
            self._append_log(r.stdout[-400:] or r.stderr[-400:])
            if r.returncode != 0:
                ok = False
                self._append_log(f"✗ Failed to install {pkg}\n")

        pip_pkgs = [n for n, t in self.missing.items() if t == "pip"]
        if pip_pkgs:
            self._set_status("Installing Python packages …", DIM)
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
            self._set_status("✓ All done! Launching app …", OK_CLR)
            self._append_log("\n✓ Setup complete — starting RAR Extractor\n")
            self.root.after(1200, self._restart)
        else:
            self._set_status("Some installs failed — check the log above", ERR_CLR)
            self.root.after(0, lambda: self.btn.configure(state="normal", text="Retry"))

    def _restart(self):
        self.root.destroy()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def run(self):
        self.root.mainloop()


def _install_quick_action():
    """Create or update the Finder Quick Action (Service)."""
    service_dir = Path.home() / "Library/Services/RAR Extractor.workflow/Contents"

    info_plist = """\
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
            <array><string>public.item</string></array>
        </dict>
    </array>
</dict>
</plist>
"""

    # Registered as a legacy Services-menu workflow on purpose: those run
    # unsandboxed, so unar can extract in place. The quickAction type runs
    # in a sandboxed Workflow Runner that macOS silently denies file
    # access, which made extraction "do nothing". Archives that still
    # fail here (wrong password, odd permissions) fall back to opening
    # the app, which auto-extracts with visible feedback.
    shell_script = (
        'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"\n'
        'fallback=()\n'
        'for f in "$@"; do\n'
        '    ext="${f##*.}"\n'
        '    case "$(echo "$ext" | tr A-Z a-z)" in\n'
        '        rar|zip|7z) ;;\n'
        '        *) continue ;;\n'
        '    esac\n'
        '    stem="${f%.*}"\n'
        '    name=$(basename "$stem")\n'
        '    mkdir -p "$stem"\n'
        '    if unar -o "$stem" -f "$f" > /tmp/rar_extractor.log 2>&1; then\n'
        '        osascript -e "display notification \\"Extracted: $name/\\" with title \\"RAR Extractor\\" sound name \\"Glass\\""\n'
        '        open "$stem"\n'
        '    else\n'
        '        rmdir "$stem" 2>/dev/null\n'
        '        fallback+=("$f")\n'
        '    fi\n'
        'done\n'
        'if [ ${#fallback[@]} -gt 0 ]; then\n'
        '    touch "/tmp/rar_extractor_auto_$(id -u)"\n'
        '    open -b dk.cadesign.rar-extractor "${fallback[@]}" 2>/dev/null || open -a "RAR Extractor" "${fallback[@]}"\n'
        'fi\n'
    )

    document_wflow = f"""\
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
                    <string>{xml_escape(shell_script)}</string>
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
"""

    wflow_path = service_dir / "document.wflow"
    # Overwrite when content changed so fixes reach users who installed
    # an older (broken) version of the workflow.
    try:
        current = wflow_path.read_text()
    except OSError:
        current = ""
    if current == document_wflow:
        return

    service_dir.mkdir(parents=True, exist_ok=True)
    (service_dir / "Info.plist").write_text(info_plist)
    wflow_path.write_text(document_wflow)
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
from tkinter import filedialog  # noqa: E402

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


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
    if n < 1024**3:  return f"{n/1024**2:.1f} MB"
    return f"{n/1024**3:.2f} GB"


def _needs_password(output: str) -> bool:
    low = output.lower()
    return any(w in low for w in ["password", "encrypted", "passphrase"])


def extract_archive(path: Path, password: str | None = None):
    """Returns (success, message, needs_password, output_dir)."""
    output_dir = path.parent / path.stem
    output_dir.mkdir(exist_ok=True)

    tool = find_tool()
    if not tool:
        return False, "unar not found — run: brew install unar", False, None

    if tool == "unar":
        cmd = ["unar"] + (["-p", password] if password else []) + \
              ["-o", str(output_dir), "-f", str(path)]
    elif tool == "unrar":
        cmd = ["unrar", "x", "-y"] + ([f"-p{password}"] if password else []) + \
              [str(path), str(output_dir) + "/"]
    else:
        cmd = [tool, "x", str(path), f"-o{output_dir}", "-y"] + \
              ([f"-p{password}"] if password else [])

    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stderr + r.stdout

    if r.returncode == 0:
        return True, f"→ {output_dir.name}/", False, output_dir

    # Don't leave an empty folder behind on failure
    try:
        output_dir.rmdir()
    except OSError:
        pass
    return False, out.strip()[:120], _needs_password(out), None


# ── Widgets ───────────────────────────────────────────────────────────────────

class DropZone(tk.Canvas):
    """Dashed-border drop target that doubles as a browse button."""

    def __init__(self, master, command, **kw):
        super().__init__(master, bg=BG, highlightthickness=0,
                         height=72, cursor="hand2", **kw)
        self._command = command
        self._active = False
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Button-1>", lambda e: self._command())
        self.bind("<Enter>", lambda e: self.set_active(True))
        self.bind("<Leave>", lambda e: self.set_active(False))

    def set_active(self, on: bool):
        self._active = on
        self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return
        color = ACCENT if self._active else BORDER
        fill  = CARD_HI if self._active else CARD
        self.create_rectangle(3, 3, w - 3, h - 3,
                              outline=color, dash=(5, 4), width=1.5,
                              fill=fill)
        self.create_text(w / 2, h / 2 - 9,
                         text="Drop archives here — or click to browse",
                         font=(FONT, 13), fill=FG if self._active else DIM)
        self.create_text(w / 2, h / 2 + 13,
                         text="RAR · ZIP · 7Z",
                         font=(FONT, 10), fill=DIM)


class PasswordDialog:
    """Dark modal password prompt. Returns str or None."""

    def __init__(self, parent, filename: str):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Password required")
        self.top.configure(bg=BG)
        self.top.resizable(False, False)
        self.top.transient(parent)

        tk.Label(self.top, text="🔒  This archive is encrypted",
                 font=(FONT, 13, "bold"), bg=BG, fg=FG).pack(padx=28, pady=(20, 2))
        tk.Label(self.top, text=filename,
                 font=(FONT, 11), bg=BG, fg=DIM).pack(padx=28)

        self.entry = tk.Entry(self.top, show="•", width=28,
                              font=(FONT, 13), bg=CARD, fg=FG,
                              insertbackground=FG, relief="flat",
                              highlightthickness=1,
                              highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        self.entry.pack(padx=28, pady=14, ipady=6)

        bar = tk.Frame(self.top, bg=BG)
        bar.pack(pady=(0, 16))
        tk.Button(bar, text="Cancel", font=(FONT, 12),
                  bg=CARD_HI, fg=FG, relief="flat", padx=14, pady=5,
                  command=self._cancel).pack(side="left", padx=4)
        tk.Button(bar, text="Extract", font=(FONT, 12, "bold"),
                  bg=ACCENT, fg="white", relief="flat", padx=16, pady=5,
                  command=self._ok).pack(side="left", padx=4)

        self.top.bind("<Return>", lambda e: self._ok())
        self.top.bind("<Escape>", lambda e: self._cancel())

        # Center over parent
        self.top.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        self.top.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 3}")

        self.entry.focus_set()
        self.top.grab_set()
        parent.wait_window(self.top)

    def _ok(self):
        self.result = self.entry.get() or None
        self.top.destroy()

    def _cancel(self):
        self.result = None
        self.top.destroy()


# ── App ───────────────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.root.title("RAR Extractor")
        self.root.geometry("600x540")
        self.root.minsize(460, 400)
        self.root.configure(bg=BG)

        self._queue: dict[Path, str] = {}        # path → tree iid
        self._extracted: dict[Path, Path] = {}   # path → output_dir
        self._lock = threading.Lock()
        self._pw_lock = threading.Lock()         # serialize password prompts
        self._pw_queue: queue.Queue = queue.Queue()
        self._extracting = False
        self._auto_extract = False   # set when opened via the Quick Action

        self._apply_styles()
        self._build()

        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>",      self._on_drop)
            self.root.dnd_bind("<<DragEnter>>", lambda e: self.zone.set_active(True))
            self.root.dnd_bind("<<DragLeave>>", lambda e: self.zone.set_active(False))

        # "Open With" from Finder
        try:
            self.root.createcommand("::tk::mac::OpenDocument", self._open_document)
        except Exception:
            pass

        # Files passed on the command line
        if len(sys.argv) > 1:
            archives = [Path(p) for p in sys.argv[1:] if is_archive(Path(p))]
            if archives:
                if self._consume_auto_marker():
                    self._auto_extract = True
                self.root.after(200, lambda: self._add_files(archives))

    # ── Styles ────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style(self.root)
        s.theme_use("default")

        s.configure("T.Treeview",
                     background=CARD, foreground=FG,
                     fieldbackground=CARD, borderwidth=0,
                     rowheight=26, font=(FONT, 12))
        s.configure("T.Treeview.Heading",
                     background=CARD_HI, foreground=DIM,
                     relief="flat", font=(FONT, 11))
        s.map("T.Treeview.Heading",
              background=[("active", CARD_HI), ("pressed", CARD_HI)],
              foreground=[("active", DIM),     ("pressed", DIM)],
              relief=[("active", "flat"),      ("pressed", "flat")])
        s.map("T.Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

        s.configure("Primary.TButton",
                     background=ACCENT, foreground="white",
                     font=(FONT, 13, "bold"), relief="flat", padding=(20, 9))
        s.map("Primary.TButton",
              background=[("active", ACCENT_HI), ("disabled", CARD_HI)],
              foreground=[("disabled", DIM)])
        s.configure("Secondary.TButton",
                     background=CARD_HI, foreground=FG,
                     font=(FONT, 12), relief="flat", padding=(14, 9))
        s.map("Secondary.TButton",
              background=[("active", "#3d3d45"), ("disabled", "#26262a")],
              foreground=[("disabled", DIM)])

        s.configure("Dark.Vertical.TScrollbar",
                     background=CARD_HI, troughcolor=CARD,
                     borderwidth=0, arrowsize=0, relief="flat")
        s.map("Dark.Vertical.TScrollbar",
              background=[("active", BORDER)])

        s.configure("Acc.Horizontal.TProgressbar",
                     background=ACCENT, troughcolor=CARD,
                     borderwidth=0, thickness=3)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self):
        # Header: logo + title side by side
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(14, 6))

        self._logo_img = self._load_logo(44)
        if self._logo_img:
            tk.Label(header, image=self._logo_img, bg=BG).pack(side="left")

        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=(10, 0))
        tk.Label(titles, text="RAR Extractor",
                 font=(FONT, 16, "bold"), bg=BG, fg=FG,
                 anchor="w").pack(fill="x")
        tk.Label(titles, text="Extract archives next to the original file",
                 font=(FONT, 10), bg=BG, fg=DIM,
                 anchor="w").pack(fill="x")

        # Drop zone
        self.zone = DropZone(self.root, command=self._browse)
        self.zone.pack(fill="x", padx=14, pady=(6, 8))

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
        self.tree.column("right", width=150, anchor="e", stretch=False)
        self.tree.tag_configure("ok",  foreground=OK_CLR)
        self.tree.tag_configure("err", foreground=ERR_CLR)
        self.tree.tag_configure("dim", foreground=DIM)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        for seq in ("<Button-2>", "<Button-3>", "<Control-Button-1>"):
            self.tree.bind(seq, self._on_tree_context)

        sb = ttk.Scrollbar(frame, orient="vertical",
                           style="Dark.Vertical.TScrollbar",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Progress bar (hidden until extraction starts)
        self.progress = ttk.Progressbar(self.root, mode="indeterminate",
                                        style="Acc.Horizontal.TProgressbar")

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

    def _load_logo(self, size: int):
        logo_path = Path(__file__).parent / "logo.png"
        if not logo_path.exists():
            return None
        try:
            from PIL import Image, ImageChops, ImageTk
            img = Image.open(str(logo_path)).convert("RGBA")
            # Make near-black background transparent: where max(R,G,B) < 30
            r, g, b, a = img.split()
            brightest = ImageChops.lighter(ImageChops.lighter(r, g), b)
            opaque = brightest.point(lambda v: 0 if v < 30 else 255)
            img.putalpha(ImageChops.darker(a, opaque))
            img = img.resize((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    # ── Open With / Apple Events ──────────────────────────────────────────

    def _consume_auto_marker(self) -> bool:
        """True if the Quick Action just launched us (marker file < 20s old)."""
        marker = Path(f"/tmp/rar_extractor_auto_{os.getuid()}")
        try:
            fresh = (time.time() - marker.stat().st_mtime) < 20
            marker.unlink()
            return fresh
        except OSError:
            return False

    def _open_document(self, *args):
        archives = [Path(p) for p in args if is_archive(Path(p))]
        if archives:
            if self._consume_auto_marker():
                self._auto_extract = True
            self.root.lift()
            self.root.focus_force()
            self._add_files(archives)

    # ── Drag & browse ─────────────────────────────────────────────────────

    def _on_drop(self, event):
        self.zone.set_active(False)
        paths = [Path(f.strip("{}")) for f in self.root.tk.splitlist(event.data)]
        archives = [p for p in paths if is_archive(p)]
        if archives:
            self._add_files(archives)

    def _browse(self):
        files = filedialog.askopenfilenames(
            title="Select archives",
            filetypes=[("Archives", "*.rar *.RAR *.zip *.ZIP *.7z *.7Z"),
                       ("All files", "*.*")],
        )
        if files:
            self._add_files([Path(f) for f in files if is_archive(Path(f))])

    # ── Queue ─────────────────────────────────────────────────────────────

    def _add_files(self, paths: list[Path]):
        new = [p for p in paths if p not in self._queue]
        if not new:
            return
        for path in new:
            iid = self.tree.insert("", "end",
                                   text=f"📦  {path.name}",
                                   values=("Reading …",), open=False,
                                   tags=("dim",))
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

    def _remove_path(self, path: Path):
        iid = self._queue.pop(path, None)
        self._extracted.pop(path, None)
        if iid:
            self.tree.delete(iid)
        self._refresh_buttons()

    def _on_tree_context(self, event):
        if self._extracting:
            return
        iid = self.tree.identify_row(event.y)
        if not iid or self.tree.parent(iid):
            return
        path = next((p for p, i in self._queue.items() if i == iid), None)
        if path is None:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Remove “{path.name}”",
                         command=lambda: self._remove_path(path))
        menu.tk_popup(event.x_root, event.y_root)

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
            self.tree.item(iid, values=("Could not read archive",), tags=("err",))
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
        total_size = 0
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
                total_size += size or 0

        noun = "file" if file_count == 1 else "files"
        self.tree.item(iid, values=(f"{file_count} {noun} · {fmt_size(total_size)}",),
                       open=True, tags=())
        self._refresh_buttons()

        # Quick Action launch: start extracting once every archive is read
        if self._auto_extract and not self._extracting:
            all_ready = all(
                self.tree.item(i, "values") != ("Reading …",)
                for i in self._queue.values()
            )
            if all_ready:
                self._auto_extract = False
                self._extract_all()

    # ── Extract ───────────────────────────────────────────────────────────

    def _extract_all(self):
        paths = list(self._queue.keys())
        if not paths or self._extracting:
            return
        self._extracting = True
        self.extract_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        n = len(paths)
        self._set_status(f"Extracting {n} {'archives' if n > 1 else 'archive'} …", DIM)
        self.progress.pack(fill="x", padx=14, pady=(6, 0))
        self.progress.start(12)

        done = {"n": 0, "ok": 0}

        def run(path: Path):
            iid = self._queue.get(path)
            if iid:
                self.root.after(0, lambda i=iid: self.tree.item(
                    i, values=("Extracting …",), tags=("dim",)))

            ok, msg, needs_pw, out_dir = extract_archive(path)

            if not ok and needs_pw:
                pwd = self._ask_password(path.name)
                if pwd:
                    ok, msg, _, out_dir = extract_archive(path, password=pwd)

            if iid:
                label = f"✓  {msg}" if ok else f"✗  {msg}"
                tag = "ok" if ok else "err"
                self.root.after(0, lambda i=iid, l=label, t=tag:
                                self.tree.item(i, values=(l,), tags=(t,)))

            with self._lock:
                if ok and out_dir:
                    self._extracted[path] = out_dir
                done["n"] += 1
                if ok:
                    done["ok"] += 1
                if done["n"] == len(paths):
                    self.root.after(0, lambda: self._on_all_done(done["ok"], len(paths)))

        for p in paths:
            threading.Thread(target=run, args=(p,), daemon=True).start()

    def _on_all_done(self, ok: int, total: int):
        self._extracting = False
        self.progress.stop()
        self.progress.pack_forget()
        if ok == total:
            self._set_status(f"✓  {ok} {'archives' if ok > 1 else 'archive'} extracted", OK_CLR)
        else:
            self._set_status(f"✓ {ok} extracted  ✗ {total - ok} failed", ERR_CLR)
        self._refresh_buttons()

    # ── Password ──────────────────────────────────────────────────────────

    def _ask_password(self, filename: str) -> str | None:
        """Prompt on the main thread; serialized so concurrent archives
        can't receive each other's passwords."""
        with self._pw_lock:
            self.root.after(0, lambda: self._pw_queue.put(
                PasswordDialog(self.root, filename).result))
            return self._pw_queue.get()

    # ── Reveal in Finder ──────────────────────────────────────────────────

    def _reveal_all(self):
        for out_dir in self._extracted.values():
            if out_dir.exists():
                subprocess.Popen(["open", str(out_dir)])

    def _on_tree_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or self.tree.parent(iid):
            return
        for path, row_iid in self._queue.items():
            if row_iid == iid and path in self._extracted:
                out_dir = self._extracted[path]
                if out_dir.exists():
                    subprocess.Popen(["open", str(out_dir)])

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_buttons(self):
        n = len(self._queue)

        if n == 0:
            self.extract_btn.configure(state="disabled", text="Extract")
        else:
            label = f"Extract  ({n})" if n > 1 else "Extract"
            ready = any(
                self.tree.item(iid, "values") not in [("Reading …",), ()]
                for iid in self._queue.values()
            )
            self.extract_btn.configure(
                text=label,
                state="normal" if (ready and not self._extracting) else "disabled")

        self.clear_btn.configure(
            state="normal" if (n > 0 and not self._extracting) else "disabled")
        self.reveal_btn.configure(
            state="normal" if self._extracted else "disabled")

    def _set_status(self, msg: str, color: str = DIM):
        self.root.after(0, lambda: self.status_lbl.configure(text=msg, fg=color))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    run_setup_if_needed()
    App().run()
