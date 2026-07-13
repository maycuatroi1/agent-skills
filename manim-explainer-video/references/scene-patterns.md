# Mẫu dựng cảnh

Các mẫu đã dùng thật và chạy tốt. Lấy về sửa, đừng phát minh lại.

---

## Luật bố cục: chống chồng chữ

Đây là lỗi hay gặp nhất và chỉ lộ ra khi xem frame, không lộ ra lúc chạy.

**Nhãn trục x đặt ở đầu mút phải**, không đặt giữa. Đáy giữa khung hình là chỗ
của caption, hai thứ sẽ đè nhau:

```python
xlab.next_to(axes.x_axis.get_end(), DOWN, buff=0.25)   # đúng
xlab.next_to(axes.x_axis, DOWN, buff=0.3)              # sai: nằm giữa, đè caption
```

**Cột bên phải gom thành một VGroup rồi mới neo vào lề.** Neo từng phần tử bằng
`next_to(cái_trước, DOWN)` sẽ tràn khỏi khung khi một phần tử rộng hơn:

```python
col = VGroup(phi, model, note).arrange(DOWN, buff=0.5)
fit(col, 4.4)                        # ép vừa bề rộng cột
col.to_edge(RIGHT, buff=0.7)
```

**Nhãn hai bên so sánh phải neo vào toạ độ cố định**, không `next_to` vào hình,
nếu không bounding box khác nhau sẽ làm hai bên lệch hàng:

```python
lab_trai.move_to(LEFT * 3.5 + UP * 1.45)
lab_phai.move_to(RIGHT * 3.5 + UP * 1.45)
```

**`fit(m, w)` chỉ thu nhỏ, không phóng to.** Dùng nó cho mọi text dài thay vì
đoán font_size.

**Đường vẽ phải nằm trong khung trục.** `axes.plot()` không cắt (clip) gì cả:
đường vượt `y_range` sẽ vẽ đè ra ngoài trục trông rất bẩn. Tính trước giá trị lớn
nhất của hàm trên khoảng đang vẽ rồi đặt `y_range` cho đủ.

---

## ValueTracker + always_redraw: xương sống của mọi animation giải thích

Cho phép "kéo một tham số, cả hình đổi theo". Đây là thứ làm video Manim khác hẳn
slide tĩnh.

```python
wt = ValueTracker(0.02)

line = always_redraw(
    lambda: axes.plot(lambda x: wt.get_value() * x + b, x_range=[32, 138],
                      color=MODEL, stroke_width=5)
)
self.play(Create(line))
self.play(wt.animate.set_value(0.075), run_time=1.7)   # đường tự xoay
```

Số chạy realtime theo cùng tracker:

```python
val = DecimalNumber(0, num_decimal_places=4, color=MODEL, font_size=30)
val.add_updater(lambda m: m.set_value(wt.get_value()))
```

`DecimalNumber` **không nhận tham số `font`** (nó dựng bằng MathTex). Truyền vào sẽ lỗi.

---

## Biến đại lượng trừu tượng thành diện tích nhìn được

Mẫu mạnh nhất trong video hồi quy: bình phương sai số vẽ thành **ô vuông thật**,
diện tích chính là giá trị. Khán giả thấy loss giảm vì ô vuông co lại, không cần
tin vào con số.

```python
y_unit = axes.c2p(0, 1)[1] - axes.c2p(0, 0)[1]   # 1 đơn vị y = bao nhiêu đơn vị màn hình

def squares():
    g = VGroup()
    for x, y in zip(D.X, D.Y):
        e = predict(x) - y
        side = abs(e) * y_unit                    # cạnh = |sai số|, nên diện tích = e^2
        sq = Square(side_length=side, stroke_color=ERROR,
                    fill_color=ERROR_FILL, fill_opacity=0.55)
        sq.move_to(axes.c2p(x, min(y, predict(x))) + RIGHT * side / 2 + UP * side / 2)
        g.add(sq)
    return g

self.play(FadeIn(always_redraw(squares)))
```

Tổng quát hoá: bất cứ khi nào có đại lượng bình phương / tích / tổng tích luỹ, hỏi
"vẽ nó thành hình gì để mắt đọc được trực tiếp?"

---

## Nối hai không gian

Cho thấy "một đường ở đây = một điểm ở kia". Dùng cho quan hệ tham số và kết quả,
input và output, thời gian và tần số.

```python
# trái: không gian dữ liệu       phải: không gian tham số
line = always_redraw(lambda: ax_trai.plot(f_theo(wt.get_value()), ...))
ball = always_redraw(lambda: Dot(ax_phai.c2p(wt.get_value(), L(wt.get_value()))))
# kéo wt: cả hai đổi cùng lúc, khán giả tự nối được hai không gian
```

---

## Bảng biến thành scatter

Chuyển từ "con số" sang "hình" mà không đứt mạch:

```python
self.play(LaggedStart(
    *[TransformFromCopy(table[i + 1], dots[i]) for i in range(len(dots))],
    lag_ratio=0.16), run_time=3.0)
```

`TransformFromCopy` giữ nguyên bảng, chỉ bay bản sao sang. Bảng vẫn còn để đối chiếu.

---

## Gradient descent / lặp có nhìn thấy được

Chạy thuật toán thật trong `data.py`, trả về đường đi, rồi phát lại từng bước.
Bước sau ngắn dần vì thuật toán hội tụ, và điều đó tự nó kể chuyện:

```python
path = D.gd_1d(w0=0.020, lr=0.000018, steps=9)      # tính thật, không diễn
for i in range(1, len(path)):
    self.add(Dot(..., fill_opacity=0.3))            # để lại vệt mờ
    self.play(wt.animate.set_value(path[i][0]),
              run_time=max(0.3, 1.0 - i * 0.07))    # bước sau nhanh dần
```

---

## Sơ đồ minh hoạ: nói rõ là sơ đồ

Khi tỉ lệ thật không vẽ được (ví dụ ellipse tỉ lệ 302:1), vẽ cường điệu **nhưng
ghi con số thật lên hình** và chú thích rõ:

```python
disclaim = sub("(sơ đồ minh hoạ, hình thật còn dẹt hơn nhiều)", size=17)
```

Rồi ngay sau đó cho **kết quả chạy thật** để trả lại độ tin cậy. Cường điệu hình
mà giấu số là mất uy tín; cường điệu hình mà show số thật là dạy học tử tế.

---

## Chuyển cảnh

`section_header(self, "03  Tiêu đề", "một câu dẫn cụ thể")` trong `theme.py`:
hiện tiêu đề giữa màn, giữ 1.2s, fade. Đủ cho mọi chuyển cảnh, không cần chế thêm.

Kết mỗi cảnh bằng `self.play(FadeOut(*self.mobjects), run_time=0.7)` để cảnh sau
bắt đầu từ nền sạch, và các file mp4 ghép lại không giật.

---

## Vòng lặp làm việc

1. `./render.sh -ql` (480p15, nhanh) cho tới khi nội dung đúng.
2. Trích frame ra **xem thật**, đừng tin là ổn:
   ```bash
   ffmpeg -ss 42 -i media/videos/scenes/480p15/S03.mp4 -frames:v 1 -y /tmp/f.png
   ```
   Lỗi chồng chữ chỉ lộ ra khi nhìn. Xem ít nhất 2-3 frame mỗi cảnh.
3. `./check.sh` rồi `./render.sh` (1080p60) cho bản giao.
