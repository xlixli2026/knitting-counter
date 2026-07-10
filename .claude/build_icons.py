"""Regenerate icon-512.png, icon-180.png, and the EMPTY_ICON data URI from
icon-source.png (the owner's reference glyph: transparent bg, light-gray
fill). Pure stdlib -- no PIL/numpy. Run from anywhere; paths are relative to
the repo root (one level up from this file).

    python3 .claude/build_icons.py

Crops to the glyph's bounding box, recolors (white-on-navy for the app
icons, #ced0d3-on-transparent for the small in-app empty-state glyph), and
box-downsamples to each target size. If the source image or the palette
changes, rerun this and paste the printed data URI into EMPTY_ICON in
index.html (the img tag's src="...").
"""
import base64
import os
import struct
import sys
import zlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "icon-source.png")
BG_NAVY = (0x22, 0x28, 0x34)
FG_WHITE = (255, 255, 255)
FG_MUTED = (0xCE, 0xD0, 0xD3)


def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    w = h = bitdepth = colortype = None
    idat = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h, bitdepth, colortype = struct.unpack(">IIBB", payload[:10])
        elif tag == b"IDAT":
            idat += payload
        elif tag == b"IEND":
            break
        pos += 8 + length + 4
    raw = zlib.decompress(idat)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
    bpp = channels * (bitdepth // 8)
    stride = w * bpp
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ftype = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, channels, bytes(out)


def get_alpha(buf, ch, x, y, w):
    i = (y * w + x) * ch
    if ch == 4:
        return buf[i + 3]
    r, g, b = buf[i], buf[i + 1], buf[i + 2]
    return 255 - (r + g + b) // 3


def bbox(buf, ch, w, h, thresh=10):
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if get_alpha(buf, ch, x, y, w) > thresh:
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)
    return minx, miny, maxx, maxy


def sample_coverage(buf, ch, w, h, x0, y0, x1, y1):
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(w, x1), min(h, y1)
    if x1c <= x0c or y1c <= y0c:
        return 0.0
    total = count = 0
    for y in range(y0c, y1c):
        for x in range(x0c, x1c):
            total += get_alpha(buf, ch, x, y, w)
            count += 1
    return (total / count) / 255.0


def build(buf, ch, w, h, minx, miny, maxx, maxy, S, fg, bg, alpha_out):
    bw, bh = maxx - minx + 1, maxy - miny + 1
    side = max(bw, bh)
    pad = int(side * 0.06)
    side += pad * 2
    ox = minx - (side - bw) // 2
    oy = miny - (side - bh) // 2
    raw = bytearray()
    for oy_i in range(S):
        for ox_i in range(S):
            sx0 = ox + (ox_i * side) // S
            sx1 = ox + ((ox_i + 1) * side) // S
            sy0 = oy + (oy_i * side) // S
            sy1 = oy + ((oy_i + 1) * side) // S
            cov = sample_coverage(buf, ch, w, h, sx0, sy0, sx1, sy1)
            if alpha_out:
                raw += bytes((fg[0], fg[1], fg[2], int(cov * 255)))
            else:
                raw += bytes((
                    int(bg[0] + (fg[0] - bg[0]) * cov),
                    int(bg[1] + (fg[1] - bg[1]) * cov),
                    int(bg[2] + (fg[2] - bg[2]) * cov),
                ))
    return bytes(raw)


def encode_png(S, pixels, has_alpha):
    ch = 4 if has_alpha else 3
    stride = S * ch
    filtered = bytearray()
    for y in range(S):
        filtered.append(0)
        filtered += pixels[y * stride:(y + 1) * stride]

    def chunk(tag, payload):
        c = tag + payload
        return struct.pack(">I", len(payload)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", S, S, 8, 6 if has_alpha else 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(filtered), 9)) + chunk(b"IEND", b"")
    return png


def write_png(path, S, pixels, has_alpha):
    with open(path, "wb") as f:
        f.write(encode_png(S, pixels, has_alpha))
    print("wrote", path, S)


if __name__ == "__main__":
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC} -- save the reference glyph there first")
    w, h, ch, buf = read_png(SRC)
    minx, miny, maxx, maxy = bbox(buf, ch, w, h)

    for S, name in [(512, "icon-512.png"), (180, "icon-180.png")]:
        pixels = build(buf, ch, w, h, minx, miny, maxx, maxy, S, FG_WHITE, BG_NAVY, alpha_out=False)
        write_png(os.path.join(ROOT, name), S, pixels, has_alpha=False)

    S = 174  # 3x of the 58px .empty-icon display box
    pixels = build(buf, ch, w, h, minx, miny, maxx, maxy, S, FG_MUTED, None, alpha_out=True)
    png_bytes = encode_png(S, pixels, has_alpha=True)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    print(f"empty-icon PNG: {len(png_bytes)} bytes, {len(b64)} base64 chars")
    out_path = os.path.join(ROOT, ".claude", "empty-icon-datauri.txt")
    with open(out_path, "w") as f:
        f.write("data:image/png;base64," + b64)
    print("wrote", out_path, "-- paste its contents into EMPTY_ICON's <img src> in index.html")
