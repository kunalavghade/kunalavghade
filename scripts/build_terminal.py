"""Build the terminal-window SVGs shown in README.md.

Everything visible is a constant below; edit it and rerun `python3 scripts/build_terminal.py`.
Animations are CSS-only, run once on load and are skipped under prefers-reduced-motion.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "terminal"
LOGO_FILE = ROOT / "assets" / "logos" / "apple.svg"
SVG_NS = "http://www.w3.org/2000/svg"

# ── Content ──────────────────────────────────────────────────────────────────
NAME = "KUNAL"
FULL_NAME = "Kunal Avghade"
PROMPT_USER, PROMPT_HOST = "kunal", "mac"
PROMPT = f"{PROMPT_USER}@{PROMPT_HOST} ~ $ "
ABOUT = (
    "Backend Engineer | Distributed Systems | AI Infra",
    "Go | TypeScript | Python | Java",
    "Temporal | Kafka | Redis | Kubernetes",
    "Building TrainMesh | KubeLab | DockerLab",
    "2b || !2b",
)
LINKS = ("portfolio", "linkedin", "leetcode", "trainmesh", "kubelab", "dockerlab", "pixelbeats")
FETCH_FIELDS = (
    ("OS", "macOS"),
    ("Shell", "zsh"),
    ("Editor", "VS Code + Claude Code"),
    ("Languages", "Go / TS / Python / Java / C++"),
    ("Infra", "Temporal / Kafka / Redis / K8s"),
    ("AI", "LLM agents / RAG / MCP"),
    ("LeetCode", "Guardian / 2164"),
    ("Uptime", "coding since 2021"),
)
FETCH_TAGLINE = "Backend by day. Side projects by night."
TMUX_SEGMENT = "[main] 0:zsh*"
LETTER_COLORS = ("blue", "teal", "green", "yellow", "mauve")

# (dark, light) per colour; dark is Catppuccin Mocha, light is Latte.
PALETTE = {
    "fg": ("#cdd6f4", "#4c4f69"),
    "dim": ("#7f849c", "#8c8fa1"),
    "green": ("#a6e3a1", "#40a02b"),
    "blue": ("#89b4fa", "#1e66f5"),
    "mauve": ("#cba6f7", "#8839ef"),
    "teal": ("#94e2d5", "#179299"),
    "yellow": ("#f9e2af", "#df8e1d"),
    "red": ("#f38ba8", "#d20f39"),
}
SWATCHES = ("red", "green", "yellow", "blue", "mauve", "teal", "fg", "dim")
TRAFFIC_LIGHTS = (("#ff5f57", "#e0443e"), ("#febc2e", "#d8a123"), ("#28c840", "#1aab29"))

# 5x7 dot-matrix glyphs for the pixel name.
GLYPHS = {
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "N": "10001/11001/11001/10101/10011/10011/10001",
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
}

# ── Timing (seconds) ─────────────────────────────────────────────────────────
START_DELAY = 0.4
TYPE_PER_CHAR = 0.05
TYPE_PAUSE = 0.3
LINE_REVEAL = 0.12
LINK_REVEAL = 0.08
CURSOR_BLINK = 1.1


@dataclass(frozen=True, slots=True)
class Layout:
    """Sizes for one responsive variant of the window."""

    suffix: str
    width: int
    font: float
    pixel: float
    logo_size: int
    logo_gap: int
    bar_height: int
    title: str

    @property
    def is_compact(self) -> bool:
        return bool(self.suffix)

    @property
    def char_width(self) -> float:
        return self.font * 0.6

    @property
    def line_height(self) -> int:
        return round(self.font * 1.7)


DESKTOP = Layout("", 800, 13, 5, 110, 28, 34, f"{PROMPT_USER}@{PROMPT_HOST} — zsh — 100×30")
COMPACT = Layout("-compact", 340, 11, 3.6, 56, 14, 30, f"{PROMPT_USER}@{PROMPT_HOST} — zsh")


# ── SVG primitives ───────────────────────────────────────────────────────────
def theme_css(font: float) -> str:
    dark = "".join(f".f-{name}{{fill:{d}}}.k-{name}{{stroke:{d}}}" for name, (d, _) in PALETTE.items())
    light = "".join(f".f-{name}{{fill:{l}}}.k-{name}{{stroke:{l}}}" for name, (_, l) in PALETTE.items())
    return (
        "text{font-family:ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace;"
        f"font-size:{font:g}px}}.b{{font-weight:700}}.i{{font-style:italic}}{dark}"
        ".bar{fill:#fff;fill-opacity:.07}.cur{opacity:0;fill-opacity:.85}.cur-idle{fill-opacity:.85}"
        f"@media(prefers-color-scheme:light){{{light}.bar{{fill:#000;fill-opacity:.06}}}}"
        "@keyframes hide{from,to{opacity:0}}@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        "@media(prefers-reduced-motion:reduce){*{animation:none!important}}"
    )


def svg_document(width: float, height: float, font: float, title: str, body: str, css: str = "") -> str:
    w, h = math.ceil(width), math.ceil(height)
    return (
        f'<svg xmlns="{SVG_NS}" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">'
        f"<title id=\"t\">{escape(title)}</title><style>{theme_css(font)}{css}</style>{body}</svg>\n"
    )


def hidden_until(seconds: float) -> str:
    return f' style="animation:hide {seconds:.2f}s steps(1,end)"' if seconds > 0 else ""


def spans(parts: list[tuple[str, str]]) -> str:
    return "".join(f'<tspan class="{cls}">{escape(text)}</tspan>' for cls, text in parts)


class Scene:
    """Collects the SVG parts of one terminal session and advances its animation clock."""

    def __init__(self, layout: Layout, y: float, start: float) -> None:
        self.layout = layout
        self.y = y
        self.clock = start
        self.parts: list[str] = []
        self.keyframes: list[str] = []
        self.last_baseline = y

    def prompt(self) -> None:
        width = len(PROMPT) * self.layout.char_width
        body = spans([("f-green b", f"{PROMPT_USER}@{PROMPT_HOST}"), ("f-blue", " ~ "), ("f-fg", "$ ")])
        self.parts.append(
            f'<text x="0" y="{self.y:g}" textLength="{width:g}" xml:space="preserve"'
            f"{hidden_until(self.clock)}>{body}</text>"
        )

    def command(self, text: str) -> None:
        """Prompt, then type `text` one character at a time behind a moving block cursor."""
        layout, count = self.layout, len(text)
        x = len(PROMPT) * layout.char_width
        width = count * layout.char_width
        self.prompt()
        chars = "".join(
            f'<tspan{hidden_until(self.clock + TYPE_PAUSE + (i + 1) * TYPE_PER_CHAR)}>{escape(ch)}</tspan>'
            for i, ch in enumerate(text)
        )
        self.parts.append(
            f'<text class="f-fg" x="{x:g}" y="{self.y:g}" textLength="{width:g}" xml:space="preserve">{chars}</text>'
        )
        self._typing_cursor(x, width, count)
        self.last_baseline = self.y
        self.clock += TYPE_PAUSE + count * TYPE_PER_CHAR + TYPE_PAUSE
        self.y += layout.line_height

    def _typing_cursor(self, x: float, width: float, count: int) -> None:
        index = len(self.keyframes)
        total = 2 * TYPE_PAUSE + count * TYPE_PER_CHAR
        typing_starts = TYPE_PAUSE / total * 100
        typing_ends = (TYPE_PAUSE + count * TYPE_PER_CHAR) / total * 100
        self.keyframes.append(
            f"@keyframes c{index}{{0%{{opacity:1;transform:translateX(0)}}"
            f"{typing_starts:.2f}%{{transform:translateX(0);animation-timing-function:steps({count},end)}}"
            f"{typing_ends:.2f}%{{opacity:1;transform:translateX({width:g}px);animation-timing-function:steps(1,end)}}"
            f"100%{{opacity:0;transform:translateX({width:g}px)}}}}"
            f".c{index}{{animation:c{index} {total:.2f}s linear {self.clock:.2f}s forwards}}"
        )
        self.parts.append(
            f'<rect class="cur f-fg c{index}" x="{x:g}" y="{self.y - self.layout.font + 1:g}" '
            f'width="{self.layout.char_width:g}" height="{self.layout.font + 2:g}"/>'
        )

    def reveal(self, markup: str, step: float = 0.0) -> None:
        self.parts.append(f"<g{hidden_until(self.clock)}>{markup}</g>")
        self.clock += step

    def idle_prompt(self) -> None:
        """Final prompt with a blinking cursor, the last thing on screen."""
        self.prompt()
        layout = self.layout
        animation = (
            f"animation:hide {self.clock:.2f}s steps(1,end),"
            f"blink {CURSOR_BLINK}s steps(1,end) {self.clock:.2f}s infinite"
        )
        self.parts.append(
            f'<rect class="cur-idle f-fg" x="{len(PROMPT) * layout.char_width:g}" y="{self.y - layout.font + 1:g}" '
            f'width="{layout.char_width:g}" height="{layout.font + 2:g}" style="{animation}"/>'
        )
        self.last_baseline = self.y

    def render(self, title: str) -> str:
        return svg_document(
            self.layout.width, self.last_baseline + 10, self.layout.font, title,
            "".join(self.parts), "".join(self.keyframes),
        )


# ── Pieces of the window ─────────────────────────────────────────────────────
def pixel_name(x: float, y: float, pixel: float) -> str:
    size = round(pixel * 0.84, 2)
    letters = []
    for index, letter in enumerate(NAME):
        rects = "".join(
            f'<rect x="{x + (index * 6 + col) * pixel:g}" y="{y + row * pixel:g}" width="{size:g}" height="{size:g}" rx=".8"/>'
            for row, bits in enumerate(GLYPHS[letter].split("/"))
            for col, bit in enumerate(bits)
            if bit == "1"
        )
        letters.append(f'<g class="f-{LETTER_COLORS[index % len(LETTER_COLORS)]}">{rects}</g>')
    return "".join(letters)


def about_line(y: float, text: str, *, is_title: bool, is_tagline: bool) -> str:
    cls = "f-dim i" if is_tagline else ("f-fg b" if is_title else "f-fg")
    separator = '<tspan class="f-dim"> | </tspan>'
    body = separator.join(f'<tspan class="{cls}">{escape(part)}</tspan>' for part in text.split(" | "))
    return f'<text x="0" y="{y:g}" xml:space="preserve">{body}</text>'


def title_bar(layout: Layout) -> str:
    lights = "".join(
        f'<circle cx="{18 + i * 20}" cy="{layout.bar_height / 2:g}" r="6" fill="{fill}" stroke="{stroke}" stroke-width=".6"/>'
        for i, (fill, stroke) in enumerate(TRAFFIC_LIGHTS)
    )
    title_y = layout.bar_height / 2 + layout.font * 0.35
    return (
        f'<rect class="bar" x="0" y="0" width="{layout.width}" height="{layout.bar_height}" rx="8"/>{lights}'
        f'<text class="f-dim" x="{layout.width / 2:g}" y="{title_y:g}" text-anchor="middle">{escape(layout.title)}</text>'
    )


def build_top(layout: Layout) -> tuple[str, float]:
    scene = Scene(layout, layout.bar_height + layout.line_height + 6, START_DELAY)
    scene.parts.append(title_bar(layout))

    scene.command("whoami")
    art_top = scene.y - layout.font + 3
    art_height = 7 * layout.pixel
    art = pixel_name(0, art_top, layout.pixel)
    if layout.is_compact:
        name_y = art_top + art_height + layout.line_height
        caption = f'<text class="f-dim" x="0" y="{name_y:g}">{escape(FULL_NAME)}</text>'
        scene.y = name_y + layout.line_height * 1.4
    else:
        art_width = (len(NAME) * 6 - 1) * layout.pixel
        caption_y = art_top + art_height / 2 + layout.font * 0.35
        caption = f'<text class="f-dim" x="{art_width + 28:g}" y="{caption_y:g}">{escape(FULL_NAME)}</text>'
        scene.y = art_top + art_height + layout.line_height * 1.1
    scene.reveal(art + caption, 0.55)

    scene.command("cat about.txt")
    for index, text in enumerate(ABOUT):
        is_tagline = index == len(ABOUT) - 1
        scene.reveal(about_line(scene.y, text, is_title=index == 0, is_tagline=is_tagline), LINE_REVEAL)
        scene.y += layout.line_height
    scene.clock += 0.4
    scene.y += 6

    scene.command("ls links/")
    return scene.render(f"Terminal: {FULL_NAME}. {ABOUT[0].replace(' | ', ', ')}."), scene.clock


def build_link(layout: Layout, name: str, delay: float) -> str:
    label = f"{name}/"
    text_width = len(label) * layout.char_width
    baseline = layout.font + 3
    body = (
        f'<g{hidden_until(delay)}><text class="f-blue b" x="0" y="{baseline:g}" textLength="{text_width:g}" '
        f'xml:space="preserve">{escape(label)}</text>'
        f'<path class="k-blue" d="M0 {baseline + 3:g}H{text_width:g}" stroke-width="1" stroke-opacity=".45"/></g>'
    )
    padding = 12 if layout.is_compact else 14
    return svg_document(text_width + padding, layout.line_height + 6, layout.font, f"Open {name}", body)


def load_logo_path() -> tuple[str, float]:
    """Return the logo's path data and its viewBox size."""
    try:
        root = ET.fromstring(LOGO_FILE.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        raise RuntimeError(f"cannot read logo at {LOGO_FILE}") from exc
    view_box_size = float(root.get("viewBox", "0 0 24 24").split()[2])
    path = next((node.get("d") for node in root.iter(f"{{{SVG_NS}}}path") if node.get("d")), None)
    if not path:
        raise ValueError(f"no path data in {LOGO_FILE}")
    return path, view_box_size


def build_fetch(layout: Layout, start: float, logo: tuple[str, float]) -> str:
    char_width, line_height = layout.char_width, layout.line_height
    scene = Scene(layout, layout.font + 6, start)
    scene.command("fastfetch")
    top = scene.y
    text_x = layout.logo_size + layout.logo_gap
    key_width = (max(len(key) for key, _ in FETCH_FIELDS) + 2) * char_width

    logo_path, logo_box = logo
    scene.reveal(
        f'<g transform="translate(0 {top - layout.font + 2:g}) scale({layout.logo_size / logo_box:.4f})">'
        f'<path class="f-blue" d="{logo_path}"/></g>',
        0.1,
    )
    host = spans([("f-green b", PROMPT_USER), ("f-fg", "@"), ("f-green b", PROMPT_HOST)])
    scene.reveal(
        f'<text x="{text_x}" y="{top:g}" xml:space="preserve">{host}</text>'
        f'<path class="k-dim" d="M{text_x} {top + 8:g}h{9 * char_width:g}" stroke-width="1" stroke-opacity=".6"/>',
        LINK_REVEAL,
    )
    for index, (key, value) in enumerate(FETCH_FIELDS):
        y = top + line_height * (index + 1)
        scene.reveal(
            f'<text x="{text_x}" y="{y:g}" class="f-yellow b" textLength="{len(key) * char_width:g}" '
            f'xml:space="preserve">{escape(key)}</text>'
            f'<text x="{text_x + len(key) * char_width:g}" y="{y:g}" class="f-dim">:</text>'
            f'<text x="{text_x + key_width:g}" y="{y:g}" class="f-fg">{escape(value)}</text>',
            LINK_REVEAL,
        )

    swatch_width = 16 if layout.is_compact else 20
    swatch_y = top + line_height * len(FETCH_FIELDS) + 14
    swatches = "".join(
        f'<rect class="f-{name}" x="{text_x + i * (swatch_width + 4)}" y="{swatch_y:g}" '
        f'width="{swatch_width}" height="{swatch_width * 0.55:g}" rx="1.5"/>'
        for i, name in enumerate(SWATCHES)
    )
    scene.reveal(swatches, 0.2)
    tagline_y = swatch_y + swatch_width * 0.55 + line_height + 4
    scene.reveal(f'<text class="f-dim i" x="0" y="{tagline_y:g}">{escape(FETCH_TAGLINE)}</text>', 0.3)
    scene.y = tagline_y + line_height + 4
    scene.idle_prompt()
    fields = ", ".join(value for _, value in FETCH_FIELDS[:4])
    return scene.render(f"fastfetch: {fields}. {FETCH_TAGLINE}")


def build_status() -> str:
    width, height = 112, 20
    body = (
        f'<rect width="{width}" height="{height}" fill="#a6e3a1"/>'
        f'<text x="{width / 2:g}" y="14" text-anchor="middle" font-size="11" font-weight="700" fill="#11111b" '
        f'textLength="{width - 16}" xml:space="preserve">{escape(TMUX_SEGMENT)}</text>'
    )
    return svg_document(width, height, 11, "tmux status segment", body)


def write(name: str, svg: str) -> None:
    (OUT_DIR / name).write_text(svg, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logo = load_logo_path()
    for layout in (DESKTOP, COMPACT):
        top_svg, top_end = build_top(layout)
        write(f"terminal-top{layout.suffix}.svg", top_svg)
        links_start = top_end + 0.15
        for index, name in enumerate(LINKS):
            write(f"terminal-link-{name}{layout.suffix}.svg", build_link(layout, name, links_start + index * LINK_REVEAL))
        fetch_start = links_start + len(LINKS) * LINK_REVEAL + 0.35
        write(f"terminal-fetch{layout.suffix}.svg", build_fetch(layout, fetch_start, logo))
    write("terminal-status.svg", build_status())
    print(f"wrote {len(list(OUT_DIR.glob('*.svg')))} SVGs to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
