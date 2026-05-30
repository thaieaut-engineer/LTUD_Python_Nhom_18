--File sơ đồ class và ERD nằm trong thư mục assets

- Thành viên trong nhóm
1. Quàng Duy Thái (Trưởng nhóm)
2. Trương Hoài Sơn (Thành viên)
3. Trần Đình Dũng (Thành viên)

- Công nghệ sử dụng:
    + Python
    + MySQL
    + QT Design
    + Git, GitHub

Mô tả các chức năng của ứng dụng
1. Mục tiêu hệ thống

Xây dựng phần mềm giúp:

- Quản lý khách hàng và thú cưng
- Quản lý dịch vụ chăm sóc (tắm, cắt tỉa, khám,…)
- Đặt lịch hẹn
- Tính tiền và xuất hóa đơn
- Theo dõi doanh thu
2. Các chức năng chính

2.1 Quản lý khách hàng
- Thêm / sửa / xóa khách hàng
- Tìm kiếm khách hàng theo tên / SĐT
- Lưu thông tin:
    + Họ tên
    + Số điện thoại
    + Địa chỉ

2.2 Quản lý thú cưng
- Mỗi khách hàng có thể có nhiều thú cưng
- Thêm / sửa / xóa thú cưng
- Tìm kiếm theo tên, loài, giống, chủ
- **Nhấn vào thú cưng** → giao diện chăm sóc (lưu trú theo ngày):
    + Nhận thú / gán nhân viên chăm sóc
    + Ghi nhận cho ăn, tải ảnh/video tình trạng
    + Trạng thái khách đã nhận thú
    + Lịch sử chăm sóc, hóa đơn lưu trú
- Thông tin:
    + Tên thú cưng
    + Loài (chó, mèo,…)
    + Giống
    + Tuổi
    + Ghi chú sức khỏe

2.3 Quản lý dịch vụ
- Danh sách dịch vụ:
    + Tắm rửa
    + Cắt tỉa lông
    + Khám bệnh
    + Spa
- Thêm / sửa / xóa dịch vụ
- Giá dịch vụ

2.4 Đặt lịch hẹn
- Tạo lịch cho thú cưng
- Chọn:
    + Khách hàng
    + Thú cưng
    + Dịch vụ
    + Thời gian
- Trạng thái:
    + Chờ xử lý
    + Đang thực hiện
    + Hoàn thành

2.5 Thanh toán & hóa đơn
- Tính tổng tiền theo dịch vụ
- Xuất hóa đơn
- Lưu lịch sử giao dịch

2.6 Thống kê & báo cáo
- Doanh thu theo ngày / tháng
- Số lượng khách hàng
- Dịch vụ phổ biến

2.7 Đăng nhập hệ thống
- Phân quyền:
    + Admin
    + Nhân viên

2.8 Bán đồ ăn / phụ kiện
- Quản lý sản phẩm (đồ ăn, phụ kiện): thêm / sửa / ẩn, theo dõi tồn kho
- Tạo hóa đơn bán lẻ (POS) — không cần lịch hẹn, chọn khách hàng (hoặc khách vãng lai) + sản phẩm
- Thêm sản phẩm vào hóa đơn dịch vụ đã có
- Tự động trừ tồn kho khi tạo hóa đơn, hoàn lại khi xóa dòng

2.9 Quản lý nhân viên & phân công
- Admin quản lý người dùng (Admin / Nhân viên), tìm kiếm theo tên/username/SĐT, lọc theo role
- Admin phân công nhân viên chăm sóc cho từng lịch hẹn
- Nhân viên được phân công có thể cập nhật trạng thái + kết quả dịch vụ của lịch hẹn của mình
- Nhân viên (không phải Admin) chỉ thấy những lịch hẹn được phân công cho mình
- Lọc lịch hẹn theo nhân viên (Admin) hoặc xem riêng "Chưa phân công"

2.10 Tìm kiếm
- Khách hàng: theo tên / số điện thoại
- Dịch vụ: theo tên / mô tả
- Sản phẩm: theo tên / SKU / mô tả + lọc theo loại (đồ ăn / phụ kiện)
- Hóa đơn: theo mã HĐ / khách hàng + lọc theo loại (dịch vụ / bán lẻ)
- Nhân viên: trong dialog Quản lý người dùng

2.11 Liên kết User – Appointment, User – Invoice
- Lịch hẹn lưu `employee_id` (nhân viên phụ trách); danh sách hiển thị tên NV
- Hóa đơn lưu `created_by` (người lập); danh sách hiển thị cột "Người tạo"

2.12 Trang Nhân viên (Admin)
- Trang riêng trên sidebar (chỉ Admin): danh sách nhân viên, tìm kiếm theo
  tên / username / SĐT.
- Bảng hiển thị thông tin tổng quan: trạng thái, tổng lịch hẹn được phân
  công, số lịch hoàn thành.
- Thao tác trực tiếp: Chi tiết, Sửa thông tin, Reset mật khẩu, Khoá / Mở khoá.
- Dialog "Chi tiết nhân viên": KPI đầy đủ (lịch hẹn / HĐ dịch vụ / HĐ bán lẻ
  / tổng doanh thu) + bảng lịch hẹn gần đây + bảng hóa đơn gần đây.

2.13 Thống kê doanh số nhân viên (Trang chủ)
- Trang chủ có panel "Doanh số theo nhân viên" dùng chung bộ lọc ngày
  của dashboard (Hôm nay / 7 ngày / 30 ngày / Tháng này / Tuỳ chỉnh).
- Bảng xếp hạng nhân viên theo doanh thu (giảm dần) với các cột:
  Lịch hẹn, Hoàn thành, HĐ dịch vụ, HĐ bán lẻ, **Tổng doanh thu**.
- Doanh thu = HĐ Dịch vụ (DA_TT) của lịch hẹn NV phụ trách +
  HĐ Bán lẻ (DA_TT) do chính NV lập.
- Tự fallback "toàn thời gian" nếu khoảng đã chọn chưa có dữ liệu.

## Cài đặt cơ sở dữ liệu

Lần đầu chạy:
```
python scripts/init_db.py            # tạo schema + seed (đã có sẵn product, invoice mở rộng)
python scripts/init_db.py --demo     # seed + thêm dữ liệu mẫu (dashboard, Nutt, bán lẻ)
python scripts/seed_demo_data.py     # chỉ nạp dữ liệu mẫu (DB đã có sẵn)
python scripts/seed_demo_data.py --reset   # xóa DEMO cũ và nạp lại
python scripts/seed_demo_data.py --catalog-only   # chỉ thêm NV + sản phẩm mẫu
```

Dữ liệu mẫu bổ sung: **9 nhân viên** (`demo_nv02` … `demo_nv10`, mật khẩu `123456`) và **20 sản phẩm** (SKU `DEMO-FOOD-*`, `DEMO-ACC-*`).

Nếu bạn đang dùng database cũ (đã chạy `init_db.py` trước khi có tính năng mới), hãy chạy migration để cập nhật:
```
mysql -u root -p petcare_db < database/migrations/add_products_and_assignment.sql
```
Migration này:
- Tạo bảng `product`
- Cho phép `invoice.appointment_id` NULL, thêm `invoice.customer_id`, `invoice.invoice_type`
- Mở rộng `invoice_item` để hỗ trợ cả dịch vụ và sản phẩm
- Tạo view `v_invoice_with_creator`, `v_appointment_with_employee` cho báo cáo