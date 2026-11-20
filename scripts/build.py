"""Builds the profile's SVG images with the site's fonts embedded.

GitHub shows README images through <img>, so an SVG can't load web fonts. Each
SVG carries its own subset of Archivo and JetBrains Mono as base64 WOFF2,
trimmed to the characters it uses.

Run from anywhere:  python3 -I scripts/build.py
Needs fontTools with brotli (for WOFF2).
"""

from __future__ import annotations

import base64
import io
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
ASSETS = ROOT / "assets"

# Palette (docs/brand.md on stoutlabs.com) ------------------------------------
INK = "#120A18"
AUBERGINE = "#2A1235"
PLUM = "#3B1450"
CREAM = "#F7EEDF"
CREMA = "#F3E4C9"
MAGENTA = "#FF3FA4"
COPPER = "#C96A3D"
VIOLET = "#8B5CF6"
LINE = "rgba(247,238,223,0.16)"


# Fonts ------------------------------------------------------------------------
class Face:
    """A static font face: measures text and emits a subset @font-face."""

    def __init__(self, family: str, font: TTFont):
        self.family = family
        self.font = font
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm
        self.used: set[str] = set()

    def width(self, text: str, size: float) -> float:
        self.used.update(text)
        total = 0
        for ch in text:
            glyph = self.cmap.get(ord(ch))
            if glyph is None:
                raise ValueError(f"{self.family} has no glyph for {ch!r}")
            total += self.hmtx[glyph][0]
        return total * size / self.upm

    def use(self, text: str) -> str:
        self.width(text, 1)
        return text

    def face_css(self) -> str:
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga", "calt"]
        options.name_IDs = []
        options.notdef_outline = True
        font = TTFont(io.BytesIO(self._bytes()))
        subsetter = subset.Subsetter(options)
        subsetter.populate(text="".join(sorted(self.used)) + " ")
        subsetter.subset(font)
        out = io.BytesIO()
        font.flavor = "woff2"
        font.save(out)
        data = base64.b64encode(out.getvalue()).decode()
        return (
            f"@font-face{{font-family:'{self.family}';"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )

    def _bytes(self) -> bytes:
        out = io.BytesIO()
        self.font.flavor = None
        self.font.save(out)
        return out.getvalue()


def archivo(weight: int, stretch: int, family: str) -> Face:
    variable = TTFont(FONTS / "archivo-latin.woff2")
    static = instancer.instantiateVariableFont(
        variable, {"wght": weight, "wdth": stretch}
    )
    return Face(family, static)


def mono(weight: int, family: str) -> Face:
    return Face(family, TTFont(FONTS / f"jetbrains-mono-normal-{weight}.woff2"))


def text(x, y, content, face: Face, size, fill, extra="") -> str:
    face.use(content)
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{face.family}" '
        f'font-size="{size}" fill="{fill}"{extra}>{escape(content)}</text>'
    )


REDUCED = "@media (prefers-reduced-motion: reduce){*{animation:none!important}.tl{opacity:1!important}.mask{display:none}}"


# Syntax tint (src/lib/highlight-code.ts on stoutlabs.com) --------------------
KEYWORDS = {
    "const", "let", "var", "function", "export", "import", "from", "return",
    "new", "class", "async", "await", "type", "interface",
}


def tint(line: str) -> list[tuple[str, str]]:
    """Splits a code line into (text, color) runs, the site's way."""
    import re

    runs: list[tuple[str, str]] = []
    plain = "rgba(247,238,223,0.9)"
    pos = 0
    for m in re.finditer(r"(//.*$)|([A-Za-z_$][A-Za-z0-9_$]*)|(\d[\d_]*)", line):
        if m.start() > pos:
            runs.append((line[pos : m.start()], plain))
        comment, word, num = m.groups()
        if comment:
            runs.append((comment, "rgba(247,238,223,0.5)"))
        elif word:
            nxt = line[m.end() : m.end() + 1]
            prev = line[m.start() - 1 : m.start()] if m.start() else ""
            if nxt == "(":
                color = VIOLET
            elif nxt == "." or prev == ".":
                color = plain
            elif word in KEYWORDS:
                color = MAGENTA
            elif word[0].isupper():
                color = VIOLET
            else:
                color = plain
            runs.append((word, color))
        else:
            runs.append((num, COPPER))
        pos = m.end()
    if pos < len(line):
        runs.append((line[pos:], plain))
    return runs


# Banner -------------------------------------------------------------------------
CODE = [
    "export const daniel = new Developer({",
    "  since: 1986, // C64, BASIC, one stick figure",
    "})",
    '  .withStack(["TypeScript", "React", "Astro", "D3"])',
    '  .withFuel(Espresso.from("DF64"))',
    "  .withHobbies(RabbitHole.ALL)",
    "  .build();",
]

TERMINAL = [
    "$ node daniel.ts",
    "[Developer] since 1986… ok",
    "[Espresso] dialed in ✓",
    "[warn] 1 new rabbit hole detected",
    "[retry 1/3] focus not found",
    "Shipped.",
]


def banner() -> str:
    W, H = 1200, 480
    display = archivo(850, 125, "ArchivoDisplay")
    body = archivo(450, 100, "ArchivoBody")
    mono5 = mono(500, "MonoMedium")
    mono4 = mono(400, "Mono")

    parts: list[str] = []

    # Poster flair: stacked arcs rising from the bottom-left corner.
    arcs = [(250, PLUM, 1), (205, COPPER, 0.22), (160, MAGENTA, 0.16), (115, PLUM, 1)]
    for r, color, opacity in arcs:
        parts.append(
            f'<path d="M {-r} {H} A {r} {r} 0 0 1 {r} {H}" fill="none" '
            f'stroke="{color}" stroke-opacity="{opacity}" stroke-width="26" '
            f'transform="translate(20 0)"/>'
        )

    # Left column ------------------------------------------------------------
    x = 64
    parts.append(text(x, 102, "stoutlabs", mono5, 40, CREAM, ' letter-spacing="-0.8"'))
    word_w = mono5.width("stoutlabs", 40) - 0.8 * 9
    parts.append(
        f'<rect class="cursor" x="{x + word_w + 3:.1f}" y="96" width="23" height="5" '
        f'fill="{MAGENTA}" filter="url(#glow)"/>'
    )

    lines = ["Full-stack", "web developer."]
    size = 58
    for i, line in enumerate(lines):
        parts.append(
            text(x, 190 + i * 60, line, display, size, CREAM, ' letter-spacing="-2.4"')
        )
    head_w = max(display.width(l, size) - 2.4 * len(l) for l in lines)

    sub = ["Data-heavy sites, fast front-ends,", "and the plumbing behind them."]
    for i, line in enumerate(sub):
        parts.append(text(x, 318 + i * 32, line, body, 24, CREMA))
    sub_w = max(body.width(l, 24) for l in sub)

    parts.append(
        text(x, 422, "self-taught · since 1986 · east tennessee", mono4, 15,
             "rgba(243,228,201,0.7)")
    )

    left_edge = x + max(head_w, sub_w)

    # Right column: the editor pane --------------------------------------------
    px, py, pw = 640, 30, 500
    code_size, code_lh = 14, 21
    term_size, term_lh = 13.5, 20
    bar_h, label_h, foot_h = 38, 24, 30
    code_h = 22 + len(CODE) * code_lh
    term_h = 20 + (len(TERMINAL) + 1) * term_lh
    ph = bar_h + code_h + label_h + term_h + foot_h

    if left_edge > px - 24:
        raise SystemExit(f"Left column runs into the pane ({left_edge:.0f}px)")

    longest = max(mono4.width(l, code_size) for l in CODE)
    if 18 + longest > pw - 12:
        raise SystemExit(f"Code is too wide for the pane ({longest:.0f}px)")

    parts.append(f'<g transform="translate({px} {py})">')
    parts.append(f'<rect width="{pw}" height="{ph}" fill="{INK}" stroke="{LINE}"/>')

    # Title bar
    parts.append(f'<line x1="0" y1="{bar_h}" x2="{pw}" y2="{bar_h}" stroke="{LINE}"/>')
    parts.append(text(16, 25, "CODE / WEB", display, 15, CREAM, ' letter-spacing="-0.4"'))
    right = "daniel.ts   main"
    rw = mono4.width(right, 12.5)
    parts.append(text(pw - 16 - rw, 24, "daniel.ts", mono4, 12.5, CREAM))
    parts.append(
        text(pw - 16 - mono4.width("main", 12.5), 24, "main", mono4, 12.5, CREMA)
    )

    # Code
    y = bar_h + 26
    for line in CODE:
        spans = "".join(
            f'<tspan fill="{color}">{escape(mono4.use(chunk))}</tspan>'
            for chunk, color in tint(line)
        )
        parts.append(
            f'<text x="18" y="{y}" font-family="{mono4.family}" font-size="{code_size}" '
            f'xml:space="preserve">{spans}</text>'
        )
        y += code_lh

    # Terminal
    ty = bar_h + code_h
    parts.append(
        f'<rect x="0" y="{ty}" width="{pw}" height="{label_h + term_h}" fill="rgba(0,0,0,0.25)"/>'
    )
    parts.append(f'<line x1="0" y1="{ty}" x2="{pw}" y2="{ty}" stroke="{LINE}"/>')
    parts.append(
        text(18, ty + 16, "TERMINAL", mono4, 10.5, "rgba(243,228,201,0.6)",
             ' letter-spacing="1.3"')
    )
    parts.append(
        f'<line x1="0" y1="{ty + label_h}" x2="{pw}" y2="{ty + label_h}" '
        f'stroke="{LINE}" stroke-opacity="0.6"/>'
    )

    clock = 0.6
    y = ty + label_h + 22
    for i, line in enumerate(TERMINAL):
        last = i == len(TERMINAL) - 1
        if line.startswith("$ "):
            command = line[2:]
            type_time = len(command) * 0.05
            spans = (
                f'<tspan fill="{MAGENTA}">$ </tspan>'
                f'<tspan fill="{CREAM}">{escape(mono4.use(command))}</tspan>'
            )
            parts.append(
                f'<text class="tl" style="animation-delay:{clock:.2f}s" x="18" y="{y}" '
                f'font-family="{mono4.family}" font-size="{term_size}" xml:space="preserve">{spans}</text>'
            )
            # A mask slides off the command, one character at a time.
            start_x = 18 + mono4.width("$ ", term_size)
            cw = mono4.width(command, term_size)
            parts.append(
                f'<rect class="mask" x="{start_x:.1f}" y="{y - 15}" width="{cw + 4:.1f}" '
                f'height="20" fill="#0e0812" style="animation:type {type_time:.2f}s '
                f'steps({len(command)}) {clock:.2f}s both"/>'
            )
            clock += type_time + 0.45
        else:
            # The site's Latin subset has no ✓, so it's drawn as a path.
            check = line.endswith(" ✓")
            if check:
                line = line[:-2]
            m = line.startswith("[") and line.index("]") + 1
            if m:
                spans = (
                    f'<tspan fill="{COPPER}">{escape(mono4.use(line[:m]))}</tspan>'
                    f'<tspan fill="rgba(243,228,201,0.85)">{escape(mono4.use(line[m:]))}</tspan>'
                )
            else:
                color = CREAM if last else "rgba(243,228,201,0.85)"
                spans = f'<tspan fill="{color}">{escape(mono4.use(line))}</tspan>'
            if line.startswith("[retry"):
                clock += 0.5
            mark = ""
            if check:
                cx = 18 + mono4.width(line + " ", term_size)
                mark = (
                    f'<path d="M{cx:.1f} {y - 4.5} l3 3.2 l5.6 -7.4" fill="none" '
                    f'stroke="{CREMA}" stroke-opacity="0.85" stroke-width="1.6" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )
            parts.append(
                f'<g class="tl" style="animation-delay:{clock:.2f}s">'
                f'<text x="18" y="{y}" font-family="{mono4.family}" font-size="{term_size}" '
                f'xml:space="preserve">{spans}</text>{mark}</g>'
            )
            clock += 0.32
        y += term_lh

    prompt_w = mono4.width("$ ", term_size)
    parts.append(
        f'<g class="tl" style="animation-delay:{clock + 0.15:.2f}s">'
        + text(18, y, "$", mono4, term_size, MAGENTA)
        + f'<rect class="cursor" x="{18 + prompt_w:.1f}" y="{y - 11}" width="8" height="14" fill="{MAGENTA}"/>'
        + "</g>"
    )

    # Status bar
    fy = ph - foot_h
    parts.append(f'<line x1="0" y1="{fy}" x2="{pw}" y2="{fy}" stroke="{LINE}"/>')
    parts.append(text(16, fy + 20, "mostly private repos", mono4, 12.5, CREMA))
    status = "TypeScript / UTF-8"
    parts.append(
        text(pw - 16 - mono4.width(status, 12.5), fy + 20, status, mono4, 12.5, CREMA)
    )
    parts.append("</g>")

    if py + ph > H - 20:
        raise SystemExit(f"Pane runs off the banner ({py + ph}px of {H})")

    style = (
        "".join(f.face_css() for f in (display, body, mono5, mono4))
        + "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        + ".cursor{animation:blink 1.15s steps(1,end) infinite}"
        + "@keyframes in{to{opacity:1}}"
        + ".tl{opacity:0;animation:in .01s linear both}"
        + ".mask{transform-box:fill-box;transform-origin:right}"
        + "@keyframes type{from{transform:scaleX(1)}to{transform:scaleX(0)}}"
        + REDUCED
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="t d">'
        f"<title id=\"t\">stoutlabs_ — Daniel Stout, full-stack web developer</title>"
        f'<desc id="d">Full-stack web developer: data-heavy sites, fast front-ends, and the '
        f"plumbing behind them. Beside it, a code editor shows daniel.ts building a Developer "
        f"since 1986 with TypeScript, React, Astro and D3.</desc>"
        f"<defs><style>{style}</style>"
        f'<filter id="glow" x="-50%" y="-200%" width="200%" height="500%">'
        f'<feGaussianBlur stdDeviation="4" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        f'<rect width="{W}" height="{H}" fill="{AUBERGINE}"/>'
        + "".join(parts)
        + "</svg>"
    )


# Skills ---------------------------------------------------------------------------
PANELS = [
    ("01", "Front-end", ["TypeScript", "JavaScript", "React", "Astro", "Next.js",
                         "Tailwind CSS", "Sass", "semantic HTML/CSS"]),
    ("02", "Data + data viz", ["D3", "large public data sets", "charts & maps",
                               "Leaflet", "data pipelines"]),
    ("03", "Back-end + data", ["Node.js", "Express", "GraphQL", "PostgreSQL", "MySQL",
                               "Strapi", "Docker"]),
    ("04", "Craft", ["performance / Core Web Vitals", "accessibility",
                     "responsive layout", "motion", "a designer's eye"]),
]


# How each panel's title is set: a font, a size, tracking and case.
TITLE = {"face": ("archivo", 300, 112), "size": 32, "tracking": -0.4, "lower": False}


def title_face(spec) -> Face:
    kind, weight, stretch = spec
    if kind == "mono":
        return mono(weight, "MonoTitle")
    return archivo(weight, stretch, "ArchivoTitle")


def skills(columns: int = 2, W: int = 1200) -> str:
    """The skill panels as a grid: two columns for desktop, one for phones."""
    gap = 24
    pw = (W - gap * (columns - 1)) / columns
    pad = 28
    chip_size, chip_h, chip_px, chip_gap = 16, 34, 13, 10
    display = title_face(TITLE["face"])
    mono4 = mono(400, "Mono")

    def layout(items):
        rows, row, x = [], [], 0.0
        for item in items:
            w = mono4.width(item, chip_size) + chip_px * 2
            if row and x + w > pw - pad * 2:
                rows.append(row)
                row, x = [], 0.0
            row.append((item, x, w))
            x += w + chip_gap
        rows.append(row)
        return rows

    laid = [layout(items) for _, _, items in PANELS]

    def height(rows: int) -> float:
        return 104 + rows * (chip_h + chip_gap) + pad - chip_gap

    # Each grid row is as tall as its tallest panel.
    grid_rows = [laid[i : i + columns] for i in range(0, len(laid), columns)]
    row_h = [height(max(len(r) for r in group)) for group in grid_rows]
    row_y = [sum(row_h[:k]) + gap * k for k in range(len(row_h))]
    H = row_y[-1] + row_h[-1]

    parts = []
    for i, ((num, title, _), rows) in enumerate(zip(PANELS, laid)):
        ox = (i % columns) * (pw + gap)
        oy = row_y[i // columns]
        ph = row_h[i // columns]
        parts.append(f'<g transform="translate({ox:.1f} {oy:.1f})">')
        parts.append(f'<rect x="1" y="1" width="{pw - 2:.1f}" height="{ph - 2}" fill="{AUBERGINE}" stroke="{PLUM}" stroke-width="2"/>')
        parts.append(f'<rect width="6" height="{ph}" fill="{MAGENTA if i % 2 == 0 else COPPER}"/>')
        parts.append(text(pad, 40, f"{num} / skills", mono4, 14, "rgba(243,228,201,0.7)"))
        shown = title.lower() if TITLE["lower"] else title
        parts.append(
            text(pad, 80, shown, display, TITLE["size"], CREAM,
                 f' letter-spacing="{TITLE["tracking"]}"')
        )
        y = 104
        for row in rows:
            for item, x, w in row:
                parts.append(
                    f'<rect x="{pad + x:.1f}" y="{y}" width="{w:.1f}" height="{chip_h}" fill="{PLUM}"/>'
                )
                parts.append(
                    text(pad + x + chip_px, y + 22.5, item, mono4, chip_size, CREAM)
                )
            y += chip_h + chip_gap
        parts.append("</g>")

    style = "".join(f.face_css() for f in (display, mono4))
    alt = "; ".join(f"{t}: {', '.join(items)}" for _, t, items in PANELS)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
        f'role="img" aria-labelledby="t"><title id="t">{escape(alt)}</title>'
        f"<defs><style>{style}</style></defs>"
        + "".join(parts)
        + "</svg>"
    )


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    builds = (
        ("banner.svg", banner),
        ("skills.svg", skills),
        ("skills-stacked.svg", lambda: skills(columns=1, W=480)),
    )
    for name, build in builds:
        svg = build()
        (ASSETS / name).write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
