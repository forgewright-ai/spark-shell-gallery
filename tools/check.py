#!/usr/bin/env python3
"""check.py -- the gallery's data check, and its index. Python's standard library only.

  python3 tools/check.py           check every theme and wallpaper, and that index.tsv names them as they are
  python3 tools/check.py --write   the same checks, then index.tsv written from the tree

The gallery is data alone, as spark-shell's `theme install` reads it (format 1):

  themes/NAME/look.env      FORMAT=2 and the keys a shared theme may set, each a value of its list
  themes/NAME/palette.env   the twenty THEME_* colors, each #rrggbb once
  themes/NAME/PICTURE       at most one picture, when look.env says WALLPAPER=picture
  wallpapers/NAME.EXT       one picture

A picture is a PNG or a JPEG as its name says, 4 MiB at most and 7680x4320 at most, with no
metadata (no EXIF, XMP or text chunks: a photo can carry where it was taken). No SVG, GIF,
font or script, no link, nothing executable, and nothing outside themes/ and wallpapers/ but
the repo's own files. spark-shell checks all of it again before it keeps anything.
"""
import hashlib
import os
import re
import stat
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAT_LINE = "# spark-shell gallery 1"
PICTURE_MAX = 4194304
PIXELS_MAX = (7680, 4320)
NAME = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
PICTURE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.(png|jpg|jpeg)$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# spark-shell's lists (v0.134): the curated faces, the glyph families, the dialog's animations, the drawings and scenes it
# ships, its palettes, and the words of `spark-shell theme` -- a theme by one of those names could not be used by name
FACES = ("neon", "argon", "xenon", "radon", "krypton")
FAMILIES = ("stone", "star", "banner")
ANIMATIONS = ("none", "moon", "ripple", "tide", "embers", "sun", "flight")
DRAWINGS = ("skyline", "fjord", "forest", "sunset", "hills", "dunes", "orbit", "ripples", "contours", "morning", "meadow",
            "kites", "fields", "grove", "arches", "shore", "flight", "embers",
            "onsen", "duck", "reef", "campfire", "ufo", "pigeons", "garoa", "horizon", "watch", "problem", "continue", "crossing")
PALETTES = ("catppuccin-latte", "catppuccin-mocha", "dracula", "everforest-dark", "everforest-light", "gruvbox-dark",
            "gruvbox-light", "nord", "one-light", "rose-pine-dawn", "rose-pine", "selenized-dark", "selenized-light",
            "solarized-light", "tokyonight-day", "tokyonight-night")
THEME_WORDS = ("none", "show", "list", "save", "delete", "back", "wallpaper", "text", "transparency", "animation", "glyphs",
               "icons", "spacing", "family", "face", "workspaces", "motion", "picture", "gallery", "install", "preview")
RESERVED = set(DRAWINGS) | set(PALETTES) | set(THEME_WORDS)
THEME_KEYS = ["THEME_BG", "THEME_FG", "THEME_ACCENT", "THEME_MUTED"] + ["THEME_ANSI_%d" % i for i in range(16)]
LOOK_KEYS = {
    "FORMAT": lambda v: v == "2",
    "PALETTE": lambda v: re.match(r"^[A-Za-z0-9._-]{1,40}$", v),
    "WORDS": lambda v: re.match(r"^[A-Za-z0-9 ,.-]{0,80}$", v),
    "WALLPAPER": lambda v: v in ("default", "picture") or HEX.match(v) or v in DRAWINGS,
    "PICTURE": lambda v: PICTURE_NAME.match(v),
    "FACE": lambda v: v in FACES,
    "ALPHA": lambda v: re.match(r"^(1|1\.0|0\.[5-9][0-9]?)$", v),
    "ANIMATION": lambda v: v in ANIMATIONS,
    "GLYPH_FAMILY": lambda v: v in FAMILIES,
    "BAR_GLYPHS": lambda v: v in ("signs", "words"),
    "WALLPAPER_MOTION": lambda v: v in ("on", "off"),
    "DIALOG_ICONS": lambda v: v in ("on", "off"),
    "DIALOG_SPACING": lambda v: v in ("none", "groups", "rows"),
}
REPO_FILES = {"README.md", "REVIEW.md", "LICENSE", "index.tsv", ".gitignore", "tools/check.py",
              ".github/CODEOWNERS", ".github/workflows/check.yml", ".github/pull_request_template.md"}


def picture(path):
    """-> (kind, width, height) from the header; ValueError for anything that is not a plain PNG or JPEG, or carries metadata."""
    data = open(path, "rb").read()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        pos, w = 8, None
        while pos + 8 <= len(data):
            n, = struct.unpack(">I", data[pos:pos + 4])
            kind = data[pos + 4:pos + 8]
            if pos == 8:
                if kind != b"IHDR":
                    raise ValueError("a PNG whose first chunk is not its header")
                w, h = struct.unpack(">II", data[pos + 8:pos + 16])
            if kind in (b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME"):
                raise ValueError("a PNG with metadata (%s): strip it" % kind.decode("latin-1"))
            if kind == b"IEND":
                if pos + 12 != len(data):
                    raise ValueError("a PNG with data after its end")
                return "png", w, h
            pos += 12 + n
        raise ValueError("a PNG with no end")
    if data[:3] == b"\xff\xd8\xff":
        pos, size = 2, None
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                raise ValueError("a JPEG with a broken marker")
            m = data[pos + 1]
            if m == 0xFF:
                pos += 1
                continue
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                pos += 2
                continue
            n, = struct.unpack(">H", data[pos + 2:pos + 4])
            if m == 0xE1 or m == 0xED or m == 0xFE:
                raise ValueError("a JPEG with metadata (EXIF, XMP, IPTC or a comment): strip it")
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and size is None:
                h, w = struct.unpack(">HH", data[pos + 5:pos + 9])
                size = (w, h)
            if m == 0xDA:
                if size is None:
                    raise ValueError("a JPEG with no frame header")
                return "jpeg", size[0], size[1]
            pos += 2 + n
        raise ValueError("a JPEG with no scan")
    raise ValueError("not a PNG or a JPEG")


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def keyvals(path, what):
    """-> [(key, value)] of a KEY=value file: printable ASCII, no blank keys; comments and blank lines skipped."""
    raw = open(path, "rb").read()
    if len(raw) > 8192:
        raise ValueError("%s is over 8 KiB" % what)
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        raise ValueError("%s is not plain ASCII" % what)
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
            raise ValueError("%s line %d holds a control character" % (what, i))
        m = re.match(r"^([A-Z_0-9]+)=(.*)$", line)
        if not m:
            raise ValueError("%s line %d is not KEY=value" % (what, i))
        out.append((m.group(1), m.group(2)))
    return out


def check_picture(path, what):
    st = os.lstat(path)
    if st.st_size > PICTURE_MAX:
        raise ValueError("%s is over 4 MiB" % what)
    kind, w, h = picture(path)
    ext = path.rsplit(".", 1)[-1].lower()
    if {"png": "png", "jpg": "jpeg", "jpeg": "jpeg"}.get(ext) != kind:
        raise ValueError("%s is a %s named .%s" % (what, kind, ext))
    if not (1 <= w <= PIXELS_MAX[0] and 1 <= h <= PIXELS_MAX[1]):
        raise ValueError("%s is %dx%d, past %dx%d" % (what, w, h, PIXELS_MAX[0], PIXELS_MAX[1]))


def check_theme(name):
    d = os.path.join(ROOT, "themes", name)
    look = dict()
    pairs = keyvals(os.path.join(d, "look.env"), "themes/%s/look.env" % name)
    for k, v in pairs:
        if k not in LOOK_KEYS:
            raise ValueError("themes/%s/look.env holds %s, which a shared theme never sets" % (name, k))
        if k in look:
            raise ValueError("themes/%s/look.env names %s twice" % (name, k))
        if not LOOK_KEYS[k](v):
            raise ValueError("themes/%s/look.env: %s=%s is not one of its values" % (name, k, v))
        look[k] = v
    if look.get("FORMAT") != "2":
        raise ValueError("themes/%s/look.env is not FORMAT=2" % name)
    pal = dict()
    for k, v in keyvals(os.path.join(d, "palette.env"), "themes/%s/palette.env" % name):
        if k not in THEME_KEYS or not HEX.match(v) or k in pal:
            raise ValueError("themes/%s/palette.env: %s=%s is not one of the twenty colors, #rrggbb, once" % (name, k, v))
        pal[k] = v
    if len(pal) != len(THEME_KEYS):
        raise ValueError("themes/%s/palette.env has %d of the twenty colors" % (name, len(pal)))
    if contrast(pal["THEME_FG"], pal["THEME_BG"]) < 4.5:
        raise ValueError("themes/%s: the text on the ground is %.1f to 1, under 4.5 (WCAG AA)" % (name, contrast(pal["THEME_FG"], pal["THEME_BG"])))
    files = set(os.listdir(d))
    pic = look.get("PICTURE")
    if look.get("WALLPAPER") == "picture":
        if not pic or pic not in files:
            raise ValueError("themes/%s says WALLPAPER=picture, and its PICTURE is not in the folder" % name)
        check_picture(os.path.join(d, pic), "themes/%s/%s" % (name, pic))
    elif pic:
        raise ValueError("themes/%s names a PICTURE its WALLPAPER does not use" % name)
    extra = files - {"look.env", "palette.env"} - ({pic} if pic else set())
    if extra:
        raise ValueError("themes/%s holds a file that is none of its own: %s" % (name, sorted(extra)[0]))
    return sorted(files)


def walk():
    """-> the index lines, after every check; ValueError at the first finding."""
    for top, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for x in dirs + files:
            p = os.path.join(top, x)
            rel = os.path.relpath(p, ROOT)
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                raise ValueError("%s is a link" % rel)
            if stat.S_ISREG(st.st_mode):
                if st.st_mode & 0o111 and rel != "tools/check.py":
                    raise ValueError("%s is executable" % rel)
                top_dir = rel.split(os.sep)[0]
                if top_dir not in ("themes", "wallpapers") and rel.replace(os.sep, "/") not in REPO_FILES:
                    raise ValueError("%s is not a theme, a wallpaper or one of the repo's own files" % rel)
            elif not stat.S_ISDIR(st.st_mode):
                raise ValueError("%s is not a file or a folder" % rel)
    lines, names = [], {}
    tdir = os.path.join(ROOT, "themes")
    for name in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        if not NAME.match(name) or name in RESERVED:
            raise ValueError("themes/%s: a name is lowercase letters, digits and -, 40 at most, and none of spark-shell's own" % name)
        if not os.path.isdir(os.path.join(tdir, name)):
            raise ValueError("themes/%s is not a folder" % name)
        for f in check_theme(name):
            if os.path.isdir(os.path.join(tdir, name, f)):
                raise ValueError("themes/%s/%s is a folder" % (name, f))
            lines.append(("theme", name, "themes/%s/%s" % (name, f)))
        names[name] = "theme"
    wdir = os.path.join(ROOT, "wallpapers")
    for f in sorted(os.listdir(wdir)) if os.path.isdir(wdir) else []:
        name, _, ext = f.rpartition(".")
        if not PICTURE_NAME.match(f) or not NAME.match(name) or name in RESERVED:
            raise ValueError("wallpapers/%s: a wallpaper is NAME.png, NAME.jpg or NAME.jpeg, its name lowercase letters, digits and -, none of spark-shell's own" % f)
        if name in names:
            raise ValueError("wallpapers/%s: %s is a theme's name already" % (f, name))
        check_picture(os.path.join(wdir, f), "wallpapers/%s" % f)
        lines.append(("wallpaper", name, "wallpapers/%s" % f))
        names[name] = "wallpaper"
    out = [FORMAT_LINE]
    for kind, name, rel in lines:
        data = open(os.path.join(ROOT, rel), "rb").read()
        out.append("%s\t%s\t%s\t%d\t%s" % (kind, name, rel, len(data), hashlib.sha256(data).hexdigest()))
    return "\n".join(out) + "\n"


def main(argv):
    try:
        index = walk()
    except (OSError, ValueError, struct.error) as e:
        print("check: %s" % e)
        return 1
    path = os.path.join(ROOT, "index.tsv")
    if "--write" in argv[1:]:
        open(path, "w").write(index)
        print("check: ok, index.tsv written (%d files)" % (index.count("\n") - 1))
        return 0
    have = open(path).read() if os.path.exists(path) else ""
    if have != index:
        print("check: index.tsv does not name the tree as it is -- python3 tools/check.py --write")
        return 1
    print("check: ok (%d files)" % (index.count("\n") - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
