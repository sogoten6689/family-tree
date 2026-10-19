"""Vẽ ảnh bìa, hình đại diện và hình bài đăng cho nhóm Facebook "Gia Phả Hán Nôm" (chỉ dùng Pillow, không gọi mạng)."""
from PIL import Image, ImageDraw, ImageFont
import random

PAPER, PAPER2 = (243, 233, 210), (232, 218, 188)
INK, RED, GOLD, MUTED = (43, 38, 33), (140, 28, 28), (176, 141, 87), (110, 98, 84)
SONG = "/System/Library/Fonts/Supplemental/Songti.ttc"
VN_B = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
VN = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
VN_SANS = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.truetype(VN_SANS, size)


def paper(w, h, seed=7):
    img = Image.new("RGB", (w, h), PAPER)
    px = img.load()
    rnd = random.Random(seed)
    for y in range(h):  # nền giấy: dải sáng tối nhẹ theo chiều dọc + nhiễu rất nhỏ
        t = y / h
        for x in range(w):
            k = 1 - 0.07 * ((x / w - 0.5) ** 2 + (t - 0.5) ** 2) * 4
            n = rnd.randint(-3, 3)
            c = tuple(max(0, min(255, int(v * k) + n)) for v in PAPER)
            px[x, y] = c
    return img


def text_c(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def seal(d, x, y, size, char="譜", bg=RED, fg=PAPER):
    d.rounded_rectangle([x, y, x + size, y + size], radius=size // 12, fill=bg)
    d.rounded_rectangle([x + size * .06, y + size * .06, x + size * .94, y + size * .94], radius=size // 14, outline=fg, width=max(2, size // 40))
    text_c(d, (x + size / 2, y + size / 2 + size * .02), char, font(SONG, int(size * .66), 1), fg)


def faint_columns(img, x0, x1, alpha_color=(190, 170, 130)):
    d = ImageDraw.Draw(img)
    cols = ["始祖生子配葬", "世系譜記忌日", "家譜傳承子孫", "祖考妣墓祠堂"]
    f = font(SONG, 46, 1)
    step = (x1 - x0) // len(cols)
    for i, col in enumerate(cols):
        x = x1 - step * i - step // 2
        for j, ch in enumerate(col):
            d.text((x, 70 + j * 62), ch, font=f, fill=alpha_color, anchor="mm")


def cover():
    W, H = 1640, 856
    img = paper(W, H)
    faint_columns(img, 1130, 1600)
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, W - 30, H - 30], outline=GOLD, width=3)
    d.rectangle([44, 44, W - 44, H - 44], outline=GOLD, width=1)
    seal(d, 180, 250, 190)
    text_c(d, (480, 250), "GIA PHẢ", font(VN_B, 120), RED, "lm")
    text_c(d, (480, 372), "HÁN NÔM", font(VN_B, 120), INK, "lm")
    text_c(d, (180, 520), "Cùng gìn giữ, phiên âm và chia sẻ gia phả dòng họ", font(VN, 46), INK, "lm")
    d.line([180, 570, 940, 570], fill=GOLD, width=3)
    text_c(d, (180, 625), "家 譜  ·  Hán Nôm  ·  Phiên âm  ·  Dịch nháp", font(VN_SANS, 36), MUTED, "lm")
    img.save("cover_1640x856.png")


def avatar():
    S = 1080
    img = paper(S, S, seed=11)
    d = ImageDraw.Draw(img)
    d.ellipse([60, 60, S - 60, S - 60], outline=GOLD, width=6)
    seal(d, 290, 190, 500)
    text_c(d, (S / 2, 800), "GIA PHẢ", font(VN_B, 96), RED)
    text_c(d, (S / 2, 900), "HÁN NÔM", font(VN_B, 96), INK)
    img.save("avatar_1080.png")


def wrap(d, s, f, width):
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def welcome():
    W, H = 1200, 630
    img = paper(W, H, seed=5)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, W - 24, H - 24], outline=GOLD, width=3)
    seal(d, 70, 70, 120)
    text_c(d, (220, 100), "Chào mừng đến với", font(VN, 40), MUTED, "lm")
    text_c(d, (220, 160), "Gia Phả Hán Nôm", font(VN_B, 72), RED, "lm")
    items = [("1", "Nhà bạn còn gia phả chữ Hán/Nôm?"), ("2", "Gửi ảnh, nhận lại phiên âm và dịch nháp miễn phí"), ("3", "Bản gốc gia đình giữ, ảnh chỉ dùng cho nghiên cứu")]
    y = 280
    for n, t in items:
        d.ellipse([90, y - 30, 150, y + 30], fill=RED)
        text_c(d, (120, y), n, font(VN_B, 38), PAPER)
        text_c(d, (180, y), t, font(VN, 42), INK, "lm")
        y += 100
    text_c(d, (W / 2, 585), "Nhắn quản trị viên hoặc bình luận bên dưới để bắt đầu", font(VN, 30), MUTED)
    img.save("post_welcome_1200x630.png")


def guide():
    W, H = 1080, 1350
    img = paper(W, H, seed=9)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, W - 24, H - 24], outline=GOLD, width=3)
    text_c(d, (W / 2, 120), "CÁCH CHỤP GIA PHẢ", font(VN_B, 76), RED)
    text_c(d, (W / 2, 195), "để phiên âm và dịch được chính xác", font(VN, 40), MUTED)
    tips = [("Chụp thẳng góc", "đặt máy song song với trang giấy, không chụp xiên"),
            ("Đủ sáng, không chói", "gần cửa sổ ban ngày; tránh đèn flash và bóng tay"),
            ("Từng trang một", "mỗi trang một ảnh, thấy đủ 4 mép giấy, đánh số thứ tự"),
            ("Đặt phẳng", "ép nhẹ gáy sách, không để trang cong; giữ nguyên bản gốc"),
            ("Chụp cả bìa và lời tựa", "ghi thêm họ, địa phương và năm viết nếu biết")]
    y = 300
    for i, (t, s) in enumerate(tips, 1):
        d.rounded_rectangle([70, y - 70, W - 70, y + 95], radius=24, fill=(250, 244, 228), outline=GOLD, width=2)
        d.ellipse([100, y - 35, 170, y + 35], fill=RED)
        text_c(d, (135, y), str(i), font(VN_B, 44), PAPER)
        text_c(d, (205, y - 22), t, font(VN_B, 44), INK, "lm")
        lines = wrap(d, s, font(VN, 33), W - 205 - 100)
        for k, ln in enumerate(lines[:2]):
            text_c(d, (205, y + 28 + k * 38), ln, font(VN, 33), MUTED, "lm")
        y += 205
    text_c(d, (W / 2, 1290), "Gửi 3–5 trang đầu để xem trước nhé", font(VN_SANS, 34), RED)
    img.save("post_guide_1080x1350.png")


def process():
    W, H = 1200, 630
    img = paper(W, H, seed=3)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, W - 24, H - 24], outline=GOLD, width=3)
    text_c(d, (W / 2, 90), "Quy trình nhận phiên âm và dịch nháp", font(VN_B, 54), RED)
    steps = [("1", "Gửi ảnh", "3–5 trang đầu"), ("2", "Đồng ý", "cho nghiên cứu"), ("3", "Xử lý", "phiên âm, dịch nháp"), ("4", "Nhận lại", "gửi lại gia đình")]
    cw, gap, y = 230, 60, 300
    left = (W - (4 * cw + 3 * gap)) // 2
    for i, (n, t, s) in enumerate(steps):
        x = left + cw // 2 + i * (cw + gap)
        d.rounded_rectangle([x - cw // 2, y - 120, x + cw // 2, y + 120], radius=26, fill=(250, 244, 228), outline=GOLD, width=3)
        d.ellipse([x - 38, y - 105, x + 38, y - 29], fill=RED)
        text_c(d, (x, y - 67), n, font(VN_B, 48), PAPER)
        text_c(d, (x, y + 20), t, font(VN_B, 42), INK)
        text_c(d, (x, y + 75), s, font(VN, 26), MUTED)
        if i < 3:
            text_c(d, (x + cw // 2 + gap // 2, y), "➜", font(VN_SANS, 44), GOLD)
    text_c(d, (W / 2, 520), "Bản dịch là dịch nháp do máy hỗ trợ, có thể sai tên riêng.", font(VN, 32), MUTED)
    text_c(d, (W / 2, 565), "Không bán · Không công khai khi chưa được đồng ý · Được rút lại bất cứ lúc nào", font(VN, 28), INK)
    img.save("post_process_1200x630.png")


if __name__ == "__main__":
    cover(); avatar(); welcome(); guide(); process()
    print("xong")
