import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
import tempfile

# ==================================================
# UNITS
# ==================================================

def cm_to_px(cm, dpi):
    return max(1, int((cm / 2.54) * dpi))

def mm_to_px(mm, dpi):
    return int((mm / 25.4) * dpi)

# ==================================================
# PAPER SIZE
# ==================================================

def resolve_page_size(paper, dpi, custom_w_cm=None, custom_h_cm=None):
    presets_cm = {
        "a4": (21.0, 29.7),
        "a3": (29.7, 42.0),
        "12x18": (30.48, 45.72),
    }

    if paper == "custom":
        if not custom_w_cm or not custom_h_cm:
            raise ValueError("Custom size requires width + height")
        w_cm = custom_w_cm
        h_cm = custom_h_cm
    else:
        w_cm, h_cm = presets_cm[paper]

    return cm_to_px(w_cm, dpi), cm_to_px(h_cm, dpi)

# ==================================================
# AUTO TRIM
# ==================================================

def auto_trim_background(img, tol=18):
    arr = np.array(img)
    rgb = arr[:, :, :3]

    bg = np.median([rgb[0,0], rgb[0,-1], rgb[-1,0], rgb[-1,-1]], axis=0)
    diff = np.abs(rgb - bg)

    mask = np.any(diff > tol, axis=2)
    ys, xs = np.where(mask)

    if len(xs) == 0:
        return img

    return img.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))

# ==================================================
# CIRCLE
# ==================================================

def round_crop_to_circle(img_bgr, size_px):
    pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    pil = auto_trim_background(pil)
    pil = pil.resize((size_px, size_px), Image.LANCZOS)

    mask = Image.new("L", (size_px, size_px), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0,0,size_px-1,size_px-1), fill=255)
    pil.putalpha(mask)

    stroke = max(3, size_px // 150)

    outline = Image.new("RGBA", (size_px, size_px), (0,0,0,0))
    d = ImageDraw.Draw(outline)
    d.ellipse(
        (stroke//2, stroke//2, size_px-stroke//2, size_px-stroke//2),
        outline=(0,0,0,255),
        width=stroke
    )

    return Image.alpha_composite(pil, outline)

# ==================================================
# RECTANGLE
# ==================================================

def fit_image_to_rectangle(img, w, h):
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert("RGBA")
    pil = auto_trim_background(pil)

    scale = w / pil.width
    pil = pil.resize((int(pil.width*scale), int(pil.height*scale)))
    pil = pil.resize((pil.width, h))

    out = Image.new("RGBA", (w, h), (0,0,0,0))
    out.paste(pil, ((w-pil.width)//2, 0), pil)

    return out

# ==================================================
# SMART ALIGN (UPDATED FOR ASYMMETRIC MARGINS)
# ==================================================

def smart_align(page, row_items, page_w, safe_x, gap):
    # total row width INCLUDING gaps
    total = 0
    for idx, (im, _, _) in enumerate(row_items):
        total += im.width
        if idx:
            total += gap

    # Center using the Left/Right Margin (safe_x)
    start_x = safe_x + (page_w - 2*safe_x - total)//2

    cx = start_x

    for im, rx, ry in row_items:
        page.paste(im, (cx, ry), im)
        cx += im.width + gap


# ==================================================
# MAIN GENERATOR
# ==================================================

def generate_pdf_job(
    input_images,
    per_image_settings,
    paper="12x18",
    custom_w_cm=None,
    custom_h_cm=None,
    gap_mm=3,
    dpi=300,
    fill_enabled=False,
    fill_source="last",
    fill_selected_name="",
    registration_marks=True  # <--- NEW PARAMETER
):
    tmpdir = tempfile.mkdtemp()

    page_w, page_h = resolve_page_size(paper, dpi, custom_w_cm, custom_h_cm)
    gap = cm_to_px(0.2, dpi)
    
    # -------------------------------------------------------------
    # MARGIN LOGIC (UPDATED)
    # -------------------------------------------------------------
    if registration_marks:
        margin_x_mm = 5 # 15mm Left/Right for Cutter Marks
        margin_y_mm = 15   # 5mm Top/Bottom (Max Space)
    else:
        margin_x_mm = 5   # Standard 5mm everywhere
        margin_y_mm = 10   

    safe_x = mm_to_px(margin_x_mm, dpi)
    safe_y = mm_to_px(margin_y_mm, dpi)

    stickers = []
    base_images = {}

    # ---------- BUILD STICKERS ----------
    for name, path in input_images:
        s = per_image_settings[name]
        img = cv2.imread(path)

        if img is None:
            continue

        if s["shape"] == "circle":
            px = cm_to_px(s["diameterCm"], dpi)
            im = round_crop_to_circle(img, px)
        else:
            w = cm_to_px(s["widthCm"], dpi)
            h = cm_to_px(s["heightCm"], dpi)
            im = fit_image_to_rectangle(img, w, h)

        base_images[name] = im

        for _ in range(int(s["qty"])):
            stickers.append(im)

    if not stickers:
        raise RuntimeError("No stickers")

    stickers.sort(key=lambda i: i.width*i.height, reverse=True)

    pages = []
    i = 0

    # ================= PAGE LOOP =================
    while i < len(stickers):

        page = Image.new("RGB", (page_w, page_h), "white")
        row_items = []

        x = safe_x  # Start at Left Margin
        y = safe_y  # Start at Top Margin
        row = 0

        while i < len(stickers):
            st = stickers[i]

            # HEIGHT CHANGE
            if row_items and st.height != row_items[0][0].height:
                smart_align(page, row_items, page_w, safe_x, gap)
                row_items = []
                x = safe_x
                y += row + gap
                row = 0

            # WIDTH WRAP (Check against Left/Right Margin)
            if x + st.width > page_w - safe_x:
                if row_items:
                    smart_align(page, row_items, page_w, safe_x, gap)

                row_items = []
                x = safe_x
                y += row + gap
                row = 0

            # HEIGHT LIMIT (Check against Top/Bottom Margin)
            if y + st.height > page_h - safe_y:
                break

            row_items.append((st, x, y))
            row = max(row, st.height)
            x += st.width + gap
            i += 1

        # LAST ROW
        if row_items:
            smart_align(page, row_items, page_w, safe_x, gap)

        pages.append(page)

    pdf_path = os.path.join(tmpdir, "memento_world_sticker.pdf")
    pages[0].save(pdf_path, format="PDF", save_all=True, append_images=pages[1:], resolution=dpi)

    return pdf_path