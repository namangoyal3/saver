"""Generate GrabHack 2.0 submission PPT – NewAge Innovators."""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Brand colours ──────────────────────────────────────────────────────────────
LIME       = RGBColor(0xC8, 0xF0, 0x00)
TEAL_DARK  = RGBColor(0x00, 0x6E, 0x5E)
TEAL_MID   = RGBColor(0x00, 0xA8, 0x9C)
CYAN       = RGBColor(0x00, 0xD4, 0xD0)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
BLACK      = RGBColor(0x1A, 0x1A, 0x1A)
GRAB_GREEN = RGBColor(0x00, 0xB1, 0x4F)
GXS_PURPLE = RGBColor(0x7B, 0x2D, 0x8B)
GRAY_BG    = RGBColor(0xF4, 0xF4, 0xF4)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)
VR_IMG  = "/home/user/saver/vr_cover.jpg"

# ── Low-level helpers ──────────────────────────────────────────────────────────
def rect(slide, l, t, w, h, rgb):
    sp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    sp.fill.solid(); sp.fill.fore_color.rgb = rgb
    sp.line.fill.background()
    return sp

def oval(slide, l, t, w, h, line_rgb, line_pt=3.5):
    sp = slide.shapes.add_shape(9, Inches(l), Inches(t), Inches(w), Inches(h))
    sp.fill.background()
    sp.line.color.rgb = line_rgb
    sp.line.width = Pt(line_pt)
    return sp

def tb(slide, text, l, t, w, h, size=12, bold=False, color=BLACK,
       align=PP_ALIGN.LEFT, font="Calibri", wrap=True):
    txb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txb.word_wrap = wrap
    tf = txb.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text
    r.font.name = font; r.font.size = Pt(size)
    r.font.bold = bold; r.font.color.rgb = color
    return txb

def tb2(slide, runs, l, t, w, h, align=PP_ALIGN.LEFT, wrap=True):
    """Textbox with multiple (text, size, bold, color, font) run tuples."""
    txb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txb.word_wrap = wrap
    tf = txb.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.alignment = align
    for text, size, bold, color, font in runs:
        r = p.add_run(); r.text = text
        r.font.name = font; r.font.size = Pt(size)
        r.font.bold = bold; r.font.color.rgb = color
    return txb

# ── Slide 2 chrome (white bg + Grab/GrabHack2.0 header + lime footer) ─────────
def chrome(slide):
    rect(slide, 0, 0, 13.33, 7.5, WHITE)
    # "Grab" top-left
    tb(slide, "Grab", 0.18, 0.10, 1.4, 0.38, size=18, bold=True, color=GRAB_GREEN)
    # "GrabHack2.0" top-right (mixed run: GrabHack bold + 2.0 smaller)
    tb2(slide, [
        ("GrabHack", 16, True,  TEAL_DARK, "Calibri"),
        ("2.0",      11, False, TEAL_DARK, "Calibri"),
    ], l=10.2, t=0.10, w=3.0, h=0.38, align=PP_ALIGN.RIGHT)
    # Lime footer bar
    rect(slide, 0, 7.28, 13.33, 0.22, LIME)

# ── Slide 1: Cover (matches screenshot exactly) ───────────────────────────────
def slide_cover(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])

    # Full lime background
    rect(sl, 0, 0, 13.33, 7.5, LIME)

    # Concentric circles (right-centre, behind image)
    cx, cy = 9.5, 3.55
    for r_in, col, lw in [
        (3.8, CYAN,      4.0),
        (2.8, TEAL_MID,  4.0),
        (1.8, CYAN,      3.5),
        (0.9, TEAL_MID,  3.0),
    ]:
        oval(sl, cx - r_in, cy - r_in, r_in * 2, r_in * 2, col, lw)

    # VR / tech image (right half of slide)
    sl.shapes.add_picture(VR_IMG,
                          Inches(5.6), Inches(0),
                          Inches(7.73), Inches(7.5))

    # Three cyan accent bars – far right edge (over image)
    for y_bar in [2.1, 3.2, 4.3]:
        rect(sl, 12.45, y_bar, 0.88, 0.48, CYAN)

    # ── Left text block ──
    # "GrabHack" + "2.0" on same line
    tb2(sl, [
        ("GrabHack", 52, True,  TEAL_DARK, "Calibri"),
        ("2.0",      30, True,  TEAL_MID,  "Calibri"),
    ], l=0.45, t=1.45, w=5.5, h=1.0)

    tb(sl, "Shaping the Future",
       0.45, 2.52, 5.2, 0.5, size=19, bold=True, color=TEAL_DARK)

    # Divider line
    rect(sl, 0.45, 3.18, 4.8, 0.04, TEAL_DARK)

    # Team name & case study
    tb(sl, "NewAge Innovators",
       0.45, 3.30, 5.5, 0.52, size=21, bold=True, color=TEAL_DARK)
    tb(sl, "AI Saver Agent for Gig Workers",
       0.45, 3.85, 5.5, 0.48, size=16, bold=False, color=TEAL_DARK)

    # Grab Family logos
    tb(sl, "Grab Family", 0.45, 5.50, 2.5, 0.25, size=8, color=TEAL_DARK)
    tb(sl, "Grab", 0.45, 5.73, 1.1, 0.40, size=18, bold=True, color=GRAB_GREEN)
    tb(sl, "GxS",  1.62, 5.73, 1.1, 0.40, size=18, bold=True, color=GXS_PURPLE)

    # Platform partner (bottom-right)
    tb(sl, "Platform Partner  unstop",
       9.5, 6.98, 3.7, 0.35, size=8, color=TEAL_DARK, align=PP_ALIGN.RIGHT)

    return sl

# ── Slide 2: Team ─────────────────────────────────────────────────────────────
def slide_team(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Team: NewAge Innovators",
       0.5, 0.65, 9, 0.58, size=26, bold=True, color=TEAL_DARK)
    tb(sl, "AI Saver Agent for Gig Workers",
       0.5, 1.28, 9, 0.42, size=16, color=TEAL_MID)
    rect(sl, 0.5, 1.80, 12.3, 0.05, LIME)

    members = [
        ("Naman Goyal",  "Team Lead / Product & Strategy"),
        ("Suyash",       "AI / ML Engineer"),
        ("Mridul Verma", "Full-Stack Developer"),
    ]
    for i, (name, role) in enumerate(members):
        lx = 0.6 + i * 4.22
        ty = 2.20
        rect(sl, lx, ty, 3.85, 4.5, GRAY_BG)
        rect(sl, lx, ty, 3.85, 0.08, TEAL_MID)
        # Circle avatar placeholder
        av = sl.shapes.add_shape(9, Inches(lx + 1.1), Inches(ty + 0.25),
                                 Inches(1.65), Inches(1.65))
        av.fill.solid(); av.fill.fore_color.rgb = TEAL_MID
        av.line.fill.background()
        # Initials
        initials = "".join(w[0].upper() for w in name.split()[:2])
        tb(sl, initials, lx + 1.1, ty + 0.55, 1.65, 0.9,
           size=28, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        tb(sl, name, lx + 0.15, ty + 2.10, 3.55, 0.50,
           size=15, bold=True, color=TEAL_DARK, align=PP_ALIGN.CENTER)
        tb(sl, role,  lx + 0.15, ty + 2.62, 3.55, 0.65,
           size=11, color=BLACK, align=PP_ALIGN.CENTER, wrap=True)
    return sl

# ── Slide 3: Problem ──────────────────────────────────────────────────────────
def slide_problem(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Problem Statement", 0.5, 0.60, 9, 0.55, size=26, bold=True, color=TEAL_DARK)
    rect(sl, 0.5, 1.22, 12.3, 0.05, LIME)

    points = [
        ("Irregular Income",
         "Gig workers face unpredictable, volatile earnings making savings planning nearly impossible."),
        ("No Safety Net",
         "No employer-backed benefits – one bad week can wipe out a gig worker's financial stability."),
        ("Low Financial Literacy",
         "Limited access to personalised guidance leaves workers unaware of savings opportunities."),
        ("Missed Micro-Savings",
         "High-frequency trips generate untapped moments for automated, frictionless micro-savings."),
    ]
    for i, (title, body) in enumerate(points):
        col, row = i % 2, i // 2
        lx = 0.55 + col * 6.45
        ty = 1.45 + row * 2.85
        rect(sl, lx, ty, 6.1, 2.60, GRAY_BG)
        rect(sl, lx, ty, 0.12, 2.60, TEAL_MID)
        tb(sl, title, lx + 0.25, ty + 0.18, 5.65, 0.45,
           size=14, bold=True, color=TEAL_DARK)
        tb(sl, body,  lx + 0.25, ty + 0.68, 5.65, 1.70,
           size=11, color=BLACK, wrap=True)
    return sl

# ── Slide 4: Solution ─────────────────────────────────────────────────────────
def slide_solution(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Our Solution: AI Saver Agent", 0.5, 0.60, 10, 0.55,
       size=26, bold=True, color=TEAL_DARK)
    rect(sl, 0.5, 1.22, 12.3, 0.05, LIME)
    tb(sl, ("An intelligent AI agent embedded in the Grab SuperApp that helps gig workers "
            "auto-save into GXS accounts through personalised micro-savings rules, "
            "behavioural nudges, and real-time income analytics."),
       0.5, 1.35, 12.3, 0.80, size=12, color=BLACK, wrap=True)

    features = [
        ("Smart Savings Agent",
         "Conversational AI understands income patterns and auto-saves via configurable rules."),
        ("Income Analytics",
         "Real-time dashboard of earnings, trends, and savings progress across Grab services."),
        ("Goal-Based Savings",
         "Set goals (emergency fund, insurance, festival) with AI-driven milestones."),
        ("Behavioural Nudges",
         "Context-aware push notifications post-trip, on payday, or during low-activity periods."),
        ("GXS Integration",
         "One-tap deposit into GXS savings pots with competitive interest rates."),
        ("Gamification",
         "Streaks, badges, and leaderboards to build consistent saving habits."),
    ]
    for i, (title, body) in enumerate(features):
        col, row = i % 3, i // 3
        lx = 0.5 + col * 4.30
        ty = 2.30 + row * 2.35
        rect(sl, lx, ty, 4.0, 2.15, GRAY_BG)
        rect(sl, lx, ty, 4.0, 0.07, TEAL_MID)
        tb(sl, title, lx + 0.15, ty + 0.18, 3.7, 0.42,
           size=12, bold=True, color=TEAL_DARK)
        tb(sl, body,  lx + 0.15, ty + 0.65, 3.7, 1.35,
           size=10, color=BLACK, wrap=True)
    return sl

# ── Slide 5: Architecture ─────────────────────────────────────────────────────
def slide_architecture(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Technical Architecture", 0.5, 0.60, 9, 0.55, size=26, bold=True, color=TEAL_DARK)
    rect(sl, 0.5, 1.22, 12.3, 0.05, LIME)

    layers = [
        (TEAL_MID,   "User Layer",
         "Grab SuperApp  ·  Driver & Delivery Partner Interface  ·  React Native"),
        (TEAL_DARK,  "AI Agent Layer",
         "Conversational Agent  ·  Income Analyser  ·  Nudge Engine  ·  Goal Tracker  (LangChain / Claude API)"),
        (CYAN,       "Data Layer",
         "Grab Trip Data  ·  GXS Transaction API  ·  User Profiles  ·  Redis Cache  ·  PostgreSQL"),
        (GRAB_GREEN, "Banking Layer",
         "GXS Bank API  ·  Savings Pots  ·  Interest Engine  ·  KYC / Compliance"),
    ]
    for i, (col, label, desc) in enumerate(layers):
        ty = 1.45 + i * 1.38
        rect(sl, 0.5,  ty, 12.3, 1.18, GRAY_BG)
        rect(sl, 0.5,  ty, 0.14, 1.18, col)
        tb(sl, label, 0.80, ty + 0.10, 2.8, 0.40, size=12, bold=True, color=col)
        tb(sl, desc,  0.80, ty + 0.55, 11.3, 0.45, size=10, color=BLACK)
        if i < len(layers) - 1:
            tb(sl, "▼", 6.5, ty + 1.15, 0.5, 0.28,
               size=11, bold=True, color=TEAL_MID, align=PP_ALIGN.CENTER)

    tb(sl, "Stack: Python · FastAPI · LangChain · Claude API · PostgreSQL · Redis · React Native",
       0.5, 6.90, 12.3, 0.30, size=9, color=TEAL_DARK)
    return sl

# ── Slide 6: Impact ───────────────────────────────────────────────────────────
def slide_impact(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Impact & Value Proposition", 0.5, 0.60, 9, 0.55, size=26, bold=True, color=TEAL_DARK)
    rect(sl, 0.5, 1.22, 12.3, 0.05, LIME)

    metrics = [
        ("3M+",   "Grab gig workers\nacross SEA"),
        ("40%",   "Income volatility\nfor gig workers"),
        ("8x",    "Higher savings rate\nwith AI nudges"),
        ("$500M+","GXS deposit\ngrowth potential"),
    ]
    for i, (num, label) in enumerate(metrics):
        lx = 0.55 + i * 3.20
        rect(sl, lx, 1.45, 2.95, 2.05, TEAL_DARK)
        tb(sl, num,   lx + 0.1, 1.55, 2.75, 0.92,
           size=34, bold=True, color=LIME, align=PP_ALIGN.CENTER)
        tb(sl, label, lx + 0.1, 2.48, 2.75, 0.80,
           size=11, color=WHITE, align=PP_ALIGN.CENTER, wrap=True)

    for i, (title, pts) in enumerate([
        ("For Gig Workers", [
            "Build financial resilience with zero friction",
            "Personalised savings plans aligned to income cycles",
            "Access to GXS high-yield savings accounts",
        ]),
        ("For Grab / GxS", [
            "Increase GXS deposit book & ARPU",
            "Deepen platform stickiness & worker loyalty",
            "ESG impact: financial inclusion for the underserved",
        ]),
    ]):
        lx = 0.55 + i * 6.45
        rect(sl, lx, 3.75, 6.1, 3.20, GRAY_BG)
        rect(sl, lx, 3.75, 6.1, 0.08, TEAL_MID)
        tb(sl, title, lx + 0.2, 3.88, 5.7, 0.42, size=14, bold=True, color=TEAL_DARK)
        for j, pt in enumerate(pts):
            tb(sl, f"•  {pt}", lx + 0.25, 4.40 + j * 0.70, 5.65, 0.55,
               size=11, color=BLACK, wrap=True)
    return sl

# ── Slide 7: Roadmap ──────────────────────────────────────────────────────────
def slide_roadmap(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    chrome(sl)

    tb(sl, "Go-To-Market Roadmap", 0.5, 0.60, 9, 0.55, size=26, bold=True, color=TEAL_DARK)
    rect(sl, 0.5, 1.22, 12.3, 0.05, LIME)

    phases = [
        ("Phase 1\nMonth 1–3", "MVP Pilot",
         "• 5,000 Grab drivers – Singapore\n• Basic income analytics\n• Manual savings rules\n• GXS pot integration"),
        ("Phase 2\nMonth 4–6", "AI Enhancement",
         "• Natural-language AI agent\n• Smart micro-savings automation\n• Goal-based pots & nudge engine\n• Behaviour analytics v1"),
        ("Phase 3\nMonth 7–12", "Scale & Expand",
         "• All gig workers in SG\n• Rollout: MY, ID, PH\n• Gamification & community\n• Insurance micro-products"),
    ]
    for i, (phase, title, detail) in enumerate(phases):
        lx = 0.55 + i * 4.30
        rect(sl, lx, 1.45, 4.0, 5.55, GRAY_BG)
        rect(sl, lx, 1.45, 4.0, 0.85, TEAL_DARK)
        tb(sl, phase, lx + 0.18, 1.50, 3.65, 0.75,
           size=11, bold=True, color=LIME, wrap=True)
        tb(sl, title, lx + 0.18, 2.38, 3.65, 0.48,
           size=14, bold=True, color=TEAL_DARK)
        tb(sl, detail, lx + 0.18, 2.95, 3.65, 3.85,
           size=11, color=BLACK, wrap=True)
        if i < len(phases) - 1:
            tb(sl, "→", lx + 4.0, 3.85, 0.38, 0.55,
               size=18, bold=True, color=TEAL_MID)
    return sl

# ── Slide 8: Thank You ────────────────────────────────────────────────────────
def slide_thankyou(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])

    # Lime full background
    rect(sl, 0, 0, 13.33, 7.5, LIME)

    # Concentric circles (right side, same as cover)
    cx, cy = 9.5, 3.55
    for r_in, col, lw in [
        (3.8, CYAN,     4.0),
        (2.8, TEAL_MID, 4.0),
        (1.8, CYAN,     3.5),
    ]:
        oval(sl, cx - r_in, cy - r_in, r_in * 2, r_in * 2, col, lw)

    # Dark teal left block
    rect(sl, 0, 0, 7.2, 7.5, TEAL_DARK)

    # VR image on right (same as cover)
    sl.shapes.add_picture(VR_IMG,
                          Inches(5.6), Inches(0),
                          Inches(7.73), Inches(7.5))

    rect(sl, 0, 6.9, 7.2, 0.6, LIME)

    tb(sl, "GrabHack 2.0", 0.5, 1.0, 6.5, 0.65, size=26, bold=True, color=LIME)
    tb(sl, "NewAge Innovators", 0.5, 1.75, 6.5, 0.78, size=36, bold=True, color=WHITE)
    tb(sl, "AI Saver Agent for Gig Workers",
       0.5, 2.60, 6.5, 0.55, size=20, color=CYAN)
    rect(sl, 0.5, 3.30, 4.5, 0.06, LIME)
    tb(sl, "Empowering gig workers to save smarter,\nlive better, and build financial resilience.",
       0.5, 3.45, 6.5, 0.95, size=15, color=WHITE, wrap=True)
    tb(sl, "Thank You", 0.5, 5.50, 5, 0.70, size=30, bold=True, color=LIME)
    tb(sl, "Grab  |  GxS  |  Platform Partner: unstop",
       0.5, 6.92, 6.0, 0.38, size=10, color=TEAL_DARK)
    return sl

# ── Build ─────────────────────────────────────────────────────────────────────
def main():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_cover(prs)
    slide_team(prs)
    slide_problem(prs)
    slide_solution(prs)
    slide_architecture(prs)
    slide_impact(prs)
    slide_roadmap(prs)
    slide_thankyou(prs)

    out = "/home/user/saver/NewAge_Innovators_AI_Saver_Agent_GrabHack2.pptx"
    prs.save(out)
    print(f"Saved → {out}  ({prs.slides.__len__()} slides)")

if __name__ == "__main__":
    main()
