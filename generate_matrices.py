"""
Raven's Progressive Matrices Generator for Kids Mensa Trainer
=============================================================
Generates 3x3 matrix puzzles where each row and column follows
consistent rules across three properties:
  1. FILL   — how much of the shape is filled (none / half / full)
  2. SIZE   — size of the shape (small / medium / large)
  3. SYMBOL — inner marker (none / dot / cross / plus)

Each property cycles through its 3 values across the row (and
down the column) in a consistent order. The bottom-right cell is
removed and presented as the "?" along with 4 answer choices.

Output: exercises_matrices.json  (ready to merge with exercises.json)
        matrix_preview.html      (standalone preview of all puzzles)
"""

import json, math, random, copy, itertools

# ── SVG helpers ────────────────────────────────────────────────

CELL   = 90          # pixels per cell
GRID   = CELL * 3   # total grid size  270
PAD    = 6           # padding around each cell
CRAD   = 6           # corner radius for cell background

def cell_bg(col, row, shade="#f8fafc", stroke="#cbd5e1"):
    x = col * CELL + 2
    y = row * CELL + 2
    w = CELL - 4
    h = CELL - 4
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{CRAD}" fill="{shade}" stroke="{stroke}" stroke-width="1.2"/>'

def question_cell(col, row):
    x = col * CELL + 2
    y = row * CELL + 2
    w = CELL - 4
    h = CELL - 4
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{CRAD}" '
        f'fill="#fff7ed" stroke="#fb923c" stroke-width="2.5" stroke-dasharray="6 3"/>'
        f'<text x="{x+w//2}" y="{y+h//2+2}" font-size="32" text-anchor="middle" '
        f'dominant-baseline="central" fill="#fb923c" font-weight="bold">?</text>'
    )

# ── Shape drawing ───────────────────────────────────────────────
# Each shape function takes (cx, cy, size, fill_style, inner_symbol)
# fill_style : "empty" | "half" | "full"
# inner_symbol: "none" | "dot" | "cross" | "plus"

def draw_circle(cx, cy, sz, fill_style, symbol):
    r = sz // 2
    parts = []
    if fill_style == "empty":
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="white" stroke="black" stroke-width="2.2"/>')
    elif fill_style == "full":
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="black" stroke="black" stroke-width="1.5"/>')
    else:  # half — left half black
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="white" stroke="black" stroke-width="2"/>')
        # clip left semicircle
        uid = f"cl{cx}{cy}"
        parts.append(
            f'<clipPath id="{uid}"><rect x="{cx-r-2}" y="{cy-r-2}" width="{r+2}" height="{r*2+4}"/></clipPath>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="black" clip-path="url(#{uid})"/>'
        )
    parts.append(draw_symbol(cx, cy, sz, symbol, fill_style))
    return "".join(parts)

def draw_square(cx, cy, sz, fill_style, symbol):
    h = sz
    x0, y0 = cx - h//2, cy - h//2
    parts = []
    if fill_style == "empty":
        parts.append(f'<rect x="{x0}" y="{y0}" width="{h}" height="{h}" fill="white" stroke="black" stroke-width="2.2"/>')
    elif fill_style == "full":
        parts.append(f'<rect x="{x0}" y="{y0}" width="{h}" height="{h}" fill="black" stroke="black" stroke-width="1.5"/>')
    else:  # half — diagonal fill top-left triangle
        parts.append(f'<rect x="{x0}" y="{y0}" width="{h}" height="{h}" fill="white" stroke="black" stroke-width="2"/>')
        # top-left triangle (like the image)
        pts = f"{x0},{y0} {x0+h},{y0} {x0},{y0+h}"
        parts.append(f'<polygon points="{pts}" fill="black"/>')
    parts.append(draw_symbol(cx, cy, sz, symbol, fill_style))
    return "".join(parts)

def draw_triangle(cx, cy, sz, fill_style, symbol):
    h = int(sz * 0.9)
    r = h // 2
    # equilateral pointing up
    tx, ty = cx, cy - int(h * 0.55)
    bl = (cx - r, cy + int(h * 0.45))
    br = (cx + r, cy + int(h * 0.45))
    pts = f"{tx},{ty} {br[0]},{br[1]} {bl[0]},{bl[1]}"
    parts = []
    if fill_style == "empty":
        parts.append(f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="2.2"/>')
    elif fill_style == "full":
        parts.append(f'<polygon points="{pts}" fill="black" stroke="black" stroke-width="1.5"/>')
    else:  # half — left half black
        parts.append(f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="2"/>')
        # left half: top vertex + bottom-left vertex + midpoint of base
        mx, my = (tx + bl[0])//2, (ty + bl[1])//2   # left edge midpoint
        bm = ((bl[0]+br[0])//2, bl[1])               # base midpoint
        half_pts = f"{tx},{ty} {bm[0]},{bm[1]} {bl[0]},{bl[1]}"
        parts.append(f'<polygon points="{half_pts}" fill="black"/>')
    parts.append(draw_symbol(cx, cy, sz, symbol, fill_style))
    return "".join(parts)

def draw_diamond(cx, cy, sz, fill_style, symbol):
    r = sz // 2
    pts = f"{cx},{cy-r} {cx+r},{cy} {cx},{cy+r} {cx-r},{cy}"
    parts = []
    if fill_style == "empty":
        parts.append(f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="2.2"/>')
    elif fill_style == "full":
        parts.append(f'<polygon points="{pts}" fill="black" stroke="black" stroke-width="1.5"/>')
    else:
        parts.append(f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="2"/>')
        uid = f"dl{cx}{cy}"
        parts.append(
            f'<clipPath id="{uid}"><rect x="{cx-r-2}" y="{cy-r-2}" width="{r+2}" height="{r*2+4}"/></clipPath>'
            f'<polygon points="{pts}" fill="black" clip-path="url(#{uid})"/>'
        )
    parts.append(draw_symbol(cx, cy, sz, symbol, fill_style))
    return "".join(parts)

SHAPE_FNS = {
    "circle":   draw_circle,
    "square":   draw_square,
    "triangle": draw_triangle,
    "diamond":  draw_diamond,
}

def draw_symbol(cx, cy, sz, symbol, fill_style):
    """Draw an inner marker — colour is white if shape is full, else black."""
    if symbol == "none":
        return ""
    col = "white" if fill_style == "full" else "black"
    r = max(3, sz // 8)
    sw = max(1.5, sz / 18)
    if symbol == "dot":
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}"/>'
    elif symbol == "cross":
        d = r * 2
        return (
            f'<line x1="{cx-d}" y1="{cy-d}" x2="{cx+d}" y2="{cy+d}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<line x1="{cx+d}" y1="{cy-d}" x2="{cx-d}" y2="{cy+d}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
        )
    elif symbol == "plus":
        d = r * 2
        return (
            f'<line x1="{cx}" y1="{cy-d}" x2="{cx}" y2="{cy+d}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<line x1="{cx-d}" y1="{cy}" x2="{cx+d}" y2="{cy}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
        )
    return ""

# ── Cell SVG renderer ────────────────────────────────────────────

def render_cell(col, row, spec, cell_size=CELL):
    """
    spec = {shape, size_code, fill, symbol}
    size_code: "small"|"medium"|"large"
    """
    cx = col * cell_size + cell_size // 2
    cy = row * cell_size + cell_size // 2
    sizes = {"small": int(cell_size * 0.28), "medium": int(cell_size * 0.42), "large": int(cell_size * 0.56)}
    sz = sizes[spec["size"]]
    fn = SHAPE_FNS[spec["shape"]]
    return fn(cx, cy, sz, spec["fill"], spec["symbol"])

# ── Matrix generation ────────────────────────────────────────────

FILLS   = ["empty", "half", "full"]
SIZES   = ["small", "medium", "large"]
SYMBOLS = ["none", "dot", "plus", "cross"]

def make_matrix(shape, fill_order, size_order, symbol_order):
    """
    Build a 3x3 matrix spec.
    *_order: list of 3 values.  Row r, col c → index (r+c)%3
    Returns list of 9 dicts, row-major.
    """
    cells = []
    for row in range(3):
        for col in range(3):
            idx = (row + col) % 3
            cells.append({
                "shape":  shape,
                "fill":   fill_order[idx],
                "size":   size_order[idx],
                "symbol": symbol_order[idx],
            })
    return cells  # index 8 = bottom-right = answer

def build_svg_grid(cells, hide_last=True, cell_size=CELL):
    """Render a 3x3 grid SVG. hide_last=True shows ? in bottom-right."""
    total = cell_size * 3
    # outer border
    svg_parts = [
        f'<svg width="100%" viewBox="0 0 {total} {total}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{total}" height="{total}" rx="12" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="2"/>',
    ]
    # grid lines
    for i in range(1, 3):
        p = i * cell_size
        svg_parts.append(f'<line x1="{p}" y1="4" x2="{p}" y2="{total-4}" stroke="#cbd5e1" stroke-width="1.2"/>')
        svg_parts.append(f'<line x1="4" y1="{p}" x2="{total-4}" y2="{p}" stroke="#cbd5e1" stroke-width="1.2"/>')

    for idx, spec in enumerate(cells):
        row, col = divmod(idx, 3)
        if hide_last and idx == 8:
            svg_parts.append(question_cell(col, row))
            continue
        # cell background
        svg_parts.append(cell_bg(col, row))
        svg_parts.append(render_cell(col, row, spec, cell_size))

    svg_parts.append("</svg>")
    return "".join(svg_parts)

def build_answer_svg(spec, cell_size=80):
    """Small SVG for a single answer choice."""
    total = cell_size
    parts = [
        f'<svg width="{total}" height="{total}" viewBox="0 0 {total} {total}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{total}" height="{total}" rx="10" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1.5"/>',
        render_cell(0, 0, spec, cell_size),
        '</svg>',
    ]
    return "".join(parts)

def build_answer_inline_svg(spec, label, cell_size=70):
    """Inline SVG + label string for the option button text."""
    return build_answer_svg(spec, cell_size)

# ── Distractor generation ────────────────────────────────────────

def make_distractors(correct_spec, shape, all_fills, all_sizes, all_symbols, n=3):
    """Generate n plausible wrong answers — each differs in exactly one property."""
    distractors = []
    candidates = []

    # differ in fill only
    for f in all_fills:
        if f != correct_spec["fill"]:
            candidates.append({**correct_spec, "fill": f})
    # differ in size only
    for s in all_sizes:
        if s != correct_spec["size"]:
            candidates.append({**correct_spec, "size": s})
    # differ in symbol only
    for sym in all_symbols:
        if sym != correct_spec["symbol"]:
            candidates.append({**correct_spec, "symbol": sym})
    # differ in two properties
    for f in all_fills:
        for sym in all_symbols:
            if f != correct_spec["fill"] and sym != correct_spec["symbol"]:
                candidates.append({**correct_spec, "fill": f, "symbol": sym})

    random.shuffle(candidates)
    seen = []
    for c in candidates:
        if c not in seen and c != correct_spec:
            seen.append(c)
        if len(seen) == n:
            break
    # pad if needed
    while len(seen) < n:
        seen.append({**correct_spec, "fill": random.choice(all_fills)})
    return seen[:n]

# ── Difficulty levels ────────────────────────────────────────────

CONFIGS = [
    # (difficulty, shape, fill_orders, size_orders, symbol_orders, description)

    # ── LEVEL 1 – one property changes (fill), rest constant ──────────
    dict(diff=1, shape="square",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","none","none"],
         desc="Square gets more and more filled"),
    dict(diff=1, shape="circle",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","none","none"],
         desc="Circle gets more and more filled"),
    dict(diff=1, shape="triangle",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","none","none"],
         desc="Triangle gets more and more filled"),

    # ── LEVEL 1 – size changes only ───────────────────────────────────
    dict(diff=1, shape="circle",
         fills=["empty","empty","empty"], sizes=["small","medium","large"], symbols=["none","none","none"],
         desc="Circle grows bigger across each row"),
    dict(diff=1, shape="square",
         fills=["full","full","full"], sizes=["small","medium","large"], symbols=["none","none","none"],
         desc="Filled square grows bigger"),

    # ── LEVEL 2 – two properties change (fill + symbol) ───────────────
    dict(diff=2, shape="circle",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","dot","plus"],
         desc="Circle: fill and inner symbol both change"),
    dict(diff=2, shape="square",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","cross","dot"],
         desc="Square: fill and inner symbol both change"),
    dict(diff=2, shape="triangle",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","dot","cross"],
         desc="Triangle: fill and inner symbol change"),
    dict(diff=2, shape="diamond",
         fills=["empty","half","full"], sizes=["medium","medium","medium"], symbols=["none","plus","dot"],
         desc="Diamond: fill and inner marker change"),

    # ── LEVEL 2 – fill + size ─────────────────────────────────────────
    dict(diff=2, shape="circle",
         fills=["full","half","empty"], sizes=["small","medium","large"], symbols=["none","none","none"],
         desc="Circle: both fill AND size change across rows"),
    dict(diff=2, shape="square",
         fills=["full","half","empty"], sizes=["large","medium","small"], symbols=["none","none","none"],
         desc="Square gets lighter as it shrinks"),

    # ── LEVEL 3 – all three properties change ─────────────────────────
    dict(diff=3, shape="circle",
         fills=["empty","half","full"], sizes=["large","medium","small"], symbols=["plus","dot","none"],
         desc="Circle: fill, size and symbol all cycle"),
    dict(diff=3, shape="square",
         fills=["full","half","empty"], sizes=["small","medium","large"], symbols=["dot","cross","none"],
         desc="Square: all three properties cycle"),
    dict(diff=3, shape="triangle",
         fills=["empty","full","half"], sizes=["medium","large","small"], symbols=["cross","none","dot"],
         desc="Triangle: all three properties cycle in different order"),
    dict(diff=3, shape="diamond",
         fills=["half","empty","full"], sizes=["large","small","medium"], symbols=["none","plus","cross"],
         desc="Diamond: all properties cycle, harder order"),
    dict(diff=3, shape="circle",
         fills=["full","empty","half"], sizes=["medium","small","large"], symbols=["cross","plus","dot"],
         desc="Circle: all three properties, hardest variant"),
]

# ── Build all puzzles ────────────────────────────────────────────

def generate_all(start_id=100):
    exercises = []
    used_symbols = set()

    for i, cfg in enumerate(CONFIGS):
        random.seed(42 + i)   # reproducible
        shape   = cfg["shape"]
        fills   = cfg["fills"]
        sizes   = cfg["sizes"]
        symbols = cfg["symbols"]

        cells   = make_matrix(shape, fills, sizes, symbols)
        correct = cells[8]      # bottom-right

        # Build distractors
        distractors = make_distractors(
            correct, shape,
            FILLS, SIZES, list(set(symbols)),
            n=3
        )

        # Shuffle answer options
        options_specs = [correct] + distractors
        random.shuffle(options_specs)
        correct_label = chr(65 + options_specs.index(correct))   # A/B/C/D

        # Build SVGs
        grid_svg   = build_svg_grid(cells, hide_last=True)
        answer_svgs = [build_answer_svg(s, 80) for s in options_specs]

        # Compose option labels A/B/C/D with embedded SVG
        options_html = []
        for letter, svg in zip("ABCD", answer_svgs):
            options_html.append(f"{letter}")   # we'll use graphic options in the viewer

        diff = cfg["diff"]
        ex = {
            "id":            start_id + i,
            "type":          "raven-matrix",
            "difficulty":    diff,
            "category":      "Raven's Matrix",
            "questionText":  f"Which answer completes the pattern? ({cfg['desc']})",
            "graphic":       grid_svg,
            "answerType":    "matrix-choice",
            "correctAnswer": correct_label,
            "correctSpec":   correct,
            "options":       ["A", "B", "C", "D"],
            "optionSpecs":   options_specs,
            "optionSVGs":    answer_svgs,
            "hint":          f"Look at each row: {', '.join(fills)} fill · {', '.join(sizes)} size · {', '.join(symbols)} symbol",
        }
        exercises.append(ex)

    return exercises

# ── Preview HTML ─────────────────────────────────────────────────

def build_preview_html(exercises):
    cards = []
    for ex in exercises:
        opt_html = ""
        for letter, svg in zip("ABCD", ex["optionSVGs"]):
            correct = "✅" if letter == ex["correctAnswer"] else ""
            opt_html += f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
              <div style="font-weight:700;font-size:1.1rem">{letter} {correct}</div>
              {svg}
            </div>"""

        diff_colour = ["","#15803d","#a16207","#b91c1c"][ex["difficulty"]]
        diff_bg     = ["","#dcfce7","#fef9c3","#fee2e2"][ex["difficulty"]]
        cards.append(f"""
        <div style="background:white;border-radius:20px;padding:20px;box-shadow:0 4px 20px rgba(0,0,0,.08);margin-bottom:24px">
          <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
            <span style="background:{diff_bg};color:{diff_colour};padding:4px 14px;border-radius:100px;font-weight:700;font-size:.82rem">{'⭐'*ex['difficulty']} Level {ex['difficulty']}</span>
            <span style="background:#ede9fe;color:#6d28d9;padding:4px 14px;border-radius:100px;font-weight:700;font-size:.82rem">Raven's Matrix</span>
            <span style="margin-left:auto;color:#94a3b8;font-size:.82rem">#{ex['id']}</span>
          </div>
          <p style="font-weight:700;font-size:1.05rem;margin:0 0 14px;color:#1e293b">{ex['questionText']}</p>
          <div style="max-width:280px;margin:0 auto 16px">
            {ex['graphic']}
          </div>
          <div style="display:flex;justify-content:center;gap:20px;flex-wrap:wrap">
            {opt_html}
          </div>
          <div style="margin-top:12px;background:#f8fafc;border-radius:10px;padding:8px 14px;font-size:.8rem;color:#64748b">
            💡 Hint: {ex['hint']}
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raven's Matrix Preview</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
  body{{font-family:'Nunito',sans-serif;background:#f0f4ff;margin:0;padding:20px}}
  .wrap{{max-width:700px;margin:0 auto}}
  h1{{text-align:center;color:#1e293b;font-weight:900}}
</style>
</head>
<body>
<div class="wrap">
  <h1>🧠 Raven's Matrix Puzzles — {len(exercises)} questions</h1>
  {''.join(cards)}
</div>
</body>
</html>"""

# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    random.seed(0)
    exercises = generate_all(start_id=100)

    # Write JSON
    out = {"exercises": exercises}
    with open("exercises_matrices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"✅ Written exercises_matrices.json  ({len(exercises)} puzzles)")

    # Write preview HTML
    html = build_preview_html(exercises)
    with open("matrix_preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Written matrix_preview.html")
