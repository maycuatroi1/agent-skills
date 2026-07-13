# Viết lời bình và canh nhịp

## Cue đặt ở đâu

Đặt `self.cue("...")` **ngay trước** `self.play()` mà câu đó đi kèm. Không đặt sau,
không gom thành một khối ở đầu scene.

```python
self.cue("Đổi w thì đường xoay.")
self.play(wt.animate.set_value(0.075), run_time=1.7)
```

`CueScene` ghi lại `self.renderer.time` tại đúng thời điểm đó. `build_final.py` cộng
offset bằng độ dài `.mp4` thật rồi sinh SRT. Nghĩa là **chỉnh timing animation thì
timecode phụ đề tự đổi theo**, không bao giờ phải sửa tay và không bao giờ lệch.

Quỹ thời gian của một câu = khoảng tới cue kế tiếp. Nên cue thưa thì câu được đọc
thong thả, cue dày thì phải nói nhanh.

---

## Canh nhịp: sửa cái gì khi bị cảnh báo

`build_final.py` cảnh báo khi câu dài hơn quỹ thời gian (mốc ~4,5 âm tiết/giây,
tiếng Việt mỗi từ một âm tiết nên đếm từ là đủ):

```
! câu 28 có thể hơi dài: cần ~5.1s, chỉ có 3.0s
```

Hai cách sửa, thường phải dùng cả hai:

**Rút gọn lời.** Bỏ từ đệm, bỏ vế phụ. "Đường đoán bừa cho L bằng 0 phẩy 2691"
thành "Đường đoán bừa: L bằng 0 phẩy 2691".

**Nới `self.wait()` ở chỗ đó.** Nếu đoạn đó thật sự dày thông tin thì khán giả cũng
cần thời gian nhìn, không riêng người đọc cần thời gian nói. Nới wait là đúng, không
phải là gian lận.

Đừng dồn hết vào rút gọn: cắt tới mức lời trở nên cụt và khó hiểu thì hỏng mục tiêu.
Video hồi quy ban đầu có 21/61 câu bị cảnh báo, sửa xong dài thêm 23 giây, và bản dài
hơn dễ theo dõi hơn hẳn.

---

## Viết số cho vừa đọc vừa hiển thị

Lời bình vừa làm phụ đề (mắt đọc) vừa làm bản dubbing (máy hoặc người đọc). Số phải
viết sao cho cả hai đều ổn.

Số thập phân đọc theo lối tiếng Việt: `0 phẩy 0285`, `1 phẩy 699`. TTS tiếng Việt
đọc đúng, mắt đọc cũng trôi.

Đơn vị đọc thành chữ: `85 mét vuông`, không viết `85 m²` (TTS đọc "m hai").

Số nguyên nhỏ giữ nguyên chữ số: `10 căn`, `40 bước`, `501 lần`.

Trên **màn hình** thì ngược lại: giữ `0.0285` và `85 m²` cho gọn và đúng chuẩn kỹ thuật.
Lệch nhau giữa lời bình và màn hình là bình thường và đúng.

---

## Giọng

Câu ngắn, chủ động, cụ thể. Đây là lời nói, không phải văn viết.

Nói thẳng cái đang xảy ra trên màn hình, đừng mô tả lại animation:
"Đổi w thì đường xoay" chứ không phải "Bây giờ chúng ta sẽ thấy đường thẳng xoay".

Đặt câu hỏi rồi trả lời bằng hình ở cảnh sau. Đó là cách giữ người xem:
"Nhưng dựa vào đâu mà nói đây là đường tốt nhất?" đóng một cảnh, mở cảnh tiếp.

Không dùng em-dash. Thay bằng dấu hai chấm khi vế sau giải nghĩa vế trước, dấu phẩy
khi chỉ ngắt nhịp, hoặc tách hẳn thành câu riêng. `build_final.py` và `check.sh`
đều bắt lỗi này.

Không mở đầu bằng "Trong video này chúng ta sẽ tìm hiểu về...". Vào thẳng.

Không kết bằng "Hy vọng video hữu ích". Kết bằng một câu đóng vòng lại chính câu
hỏi đã mở ở đầu.

---

## Kiểm tra sync trước khi giao

ffmpeg trên máy thiếu libass nên không burn-in được. Verify bằng cách trích frame
rồi vẽ phụ đề đang active lên bằng PIL, xem lời có khớp hình không. Chọn 4 mốc rải
đều video là đủ để bắt lỗi lệch một cảnh.
