"""Builds media/search.svg: a real-time run of examples/a343507_first8.trawl.

The times are from a real  run on one core; only the typing of the command is paced by hand. Lines
appear at set times with SVG <animate> only, so it plays inside a plain <img> on GitHub.
Run: python media/make_search_svg.py media/search.svg
"""
import sys
from html import escape

G, Y, D, T, R, B = "#7ee787", "#e3b341", "#8b949e", "#e6edf3", "#ff7b72", "#79c0ff"
LH, PAD, TOP, CW = 22, 18, 44, 8.4  # CW: one character's width at 14px monospace
TYPE_STEP = 0.045


def write(path, title, lines, loop, width=860):
    """lines: list of (t, parts) or (t, "$", command). parts = [(text, color, bold)]."""
    end = 0.985

    def k(t):
        return f"{t / loop:.4f}"

    def show(t_on, t_off=None):
        off = k(t_off) if t_off is not None else f"{end}"
        return (f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{k(t_on)};{off}" calcMode="discrete" '
                f'dur="{loop}s" repeatCount="indefinite"/>')

    def y(i):
        return TOP + LH * i + 14

    h = TOP + LH * len(lines) + PAD
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}" role="img">',
           f"<title>{escape(title)}</title>",
           "<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
           "font-size:14px;white-space:pre}</style>",
           f'<rect width="{width}" height="{h}" rx="10" fill="#0d1117"/>',
           '<circle cx="22" cy="20" r="6" fill="#ff5f57"/><circle cx="42" cy="20" r="6" fill="#febc2e"/>'
           '<circle cx="62" cy="20" r="6" fill="#28c840"/>']
    for i, line in enumerate(lines):
        t = line[0]
        if len(line) == 3:  # a typed command
            cmd = line[2]
            out.append(f'<text x="{PAD}" y="{y(i)}" fill="{G}" opacity="0">${show(t)}</text>')
            for j, ch in enumerate(cmd):
                if ch != " ":
                    out.append(f'<text x="{PAD + (j + 2) * CW:.1f}" y="{y(i)}" fill="{T}" font-weight="bold" '
                               f'opacity="0">{escape(ch)}{show(t + 0.25 + j * TYPE_STEP)}</text>')
            continue
        parts = line[1]
        if not parts:
            continue
        spans = "".join(f'<tspan fill="{c}"{" font-weight=&quot;bold&quot;" if b else ""}>{escape(s)}</tspan>'
                        .replace("&quot;", '"') for s, c, b in parts)
        out.append(f'<text x="{PAD}" y="{y(i)}" opacity="0" xml:space="preserve">{spans}{show(t)}</text>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def typed_until(t, cmd):
    """When a command started at t has finished typing."""
    return t + 0.25 + len(cmd) * TYPE_STEP


cmd = "trawl fast examples/a343507_first8.trawl"
t0 = typed_until(0.6, cmd)
runs = [(1.16, "1 5"), (1.19, "2 208"), (1.22, "3 3475"), (1.24, "4 8174"), (1.56, "5 252965"),
        (2.89, "6 3648835"), (6.00, "7 72286092"), (11.04, "8 159329607")]
L = [(0.0, [("# OEIS A343507 (Erdős problem 727): for each n, the least k with ((k+n)!)^2 dividing (2k)!", D, 0)]),
     (0.0, [("# This prints n, then a(n). Each term is searched from scratch.", D, 0)]),
     (0.6, "$", cmd)]
L += [(t0 + t, [(s.split()[0] + " ", D, 0), (s.split()[1], G, 1)]) for t, s in runs]
end = t0 + 11.05
L += [(end, [("~ done in 0:09", D, 0), ("      real time, one core, no edits", D, 0)]),
      (0.0, []),
      (end + 0.9, [("a(9) = 2935782889 was found in 2021. Then the table sat still for five years.", T, 0)]),
      (end + 2.0, [("a(10), a(11), a(12) were found in November 2026 and are now in the OEIS.", Y, 1)]),
      (end + 3.0, [("This same search reproduces them: 8 minutes, 33 minutes, about 5 hours on 6 cores.", T, 0)])]
write(sys.argv[1], "Trawl finds the first eight terms of OEIS A343507 in about 10 seconds, in real time", L, round(end + 12, 1))
