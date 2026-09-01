# Business Analysis

## 1. Tên đề tài

**Mô hình xây dựng tự động cây gia phả từ văn bản gia phả Hán Nôm**

## 2. Bối cảnh và bài toán

Gia phả Hán Nôm là nguồn tư liệu quan trọng để lưu giữ thông tin về dòng họ, quan hệ huyết thống, quê quán, vai vế, năm sinh năm mất và các ghi chép lịch sử của từng cá nhân. Tuy nhiên, phần lớn tư liệu này đang tồn tại ở dạng văn bản cổ, khó đọc, khó tra cứu và khó chuyển thành dữ liệu số có cấu trúc.

Bài toán đặt ra là xây dựng một mô hình có thể tự động tiếp nhận nội dung gia phả Hán Nôm, trích xuất thông tin quan trọng, chuẩn hóa dữ liệu và biểu diễn thành cây gia phả trực quan. Đây là một bài toán liên ngành, kết hợp xử lý ngôn ngữ, chuẩn hóa dữ liệu, mô hình hóa quan hệ và trực quan hóa thông tin.

## 3. Mục tiêu chính

Xây dựng mô hình tự động tạo cây gia phả từ văn bản gia phả Hán Nôm thông qua các bước nhận diện nội dung, trích xuất thông tin nhân vật và quan hệ gia tộc, chuẩn hóa thành dữ liệu có cấu trúc, sau đó biểu diễn dưới dạng cây hoặc đồ thị gia phả phục vụ lưu trữ, tra cứu và bảo tồn di sản văn hóa.

## 4. Mục tiêu cụ thể

1. Phân tích đặc trưng của văn bản gia phả Hán Nôm và cách biểu diễn quan hệ gia tộc trong tư liệu gốc.
2. Xây dựng quy trình tiếp nhận văn bản đầu vào và chuyển thành dữ liệu số có thể xử lý.
3. Trích xuất các thực thể chính như họ tên, giới tính, đời, cha, mẹ, vợ chồng, con cái, quê quán, năm sinh, năm mất, chức danh.
4. Xác định và chuẩn hóa các loại quan hệ gia tộc như cha con, mẹ con, vợ chồng, anh chị em.
5. Thiết kế mô hình dữ liệu biểu diễn gia phả dưới dạng cây hoặc đồ thị.
6. Xây dựng hệ thống sinh cây gia phả trực quan từ dữ liệu đã chuẩn hóa.
7. Kiểm tra tính hợp lệ của dữ liệu và đánh giá chất lượng kết quả đầu ra.

## 5. Giá trị và ý nghĩa của đề tài

### 5.1. Giá trị thực tiễn

- Hỗ trợ số hóa tư liệu gia phả truyền thống.
- Giảm công sức nhập liệu thủ công từ văn bản cổ.
- Tăng khả năng tra cứu thông tin dòng họ theo cá nhân, nhánh họ hoặc thế hệ.
- Hỗ trợ bảo tồn và phổ biến tri thức gia đình, dòng tộc trong môi trường số.

### 5.2. Giá trị khoa học và công nghệ

- Ứng dụng xử lý ngôn ngữ và trích xuất thông tin trên nguồn văn bản cổ.
- Chuẩn hóa dữ liệu gia phả thành mô hình có thể tái sử dụng cho lưu trữ và phân tích.
- Kết hợp giữa nhận dạng nội dung, mô hình dữ liệu quan hệ và trực quan hóa đồ thị.

## 6. Phân tích công việc cần làm

Để hiện thực hóa đề tài, công việc có thể chia thành các nhóm chính sau.

### 6.1. Nhóm công việc khảo sát và phân tích nghiệp vụ

1. Thu thập mẫu văn bản gia phả Hán Nôm hoặc bản phiên âm, dịch nghĩa.
2. Phân tích cấu trúc thường gặp trong gia phả: tên người, vai vế, nhánh họ, đời, quan hệ.
3. Xác định bài toán đầu vào và đầu ra của hệ thống.
4. Xây dựng bộ tiêu chí đánh giá độ đúng của cây gia phả sinh ra.

### 6.2. Nhóm công việc tiền xử lý dữ liệu

1. Chuẩn hóa văn bản đầu vào từ ảnh, OCR hoặc văn bản số.
2. Tách đoạn, tách câu, tách dòng thông tin liên quan đến từng cá nhân.
3. Xử lý khác biệt về cách ghi tên, niên đại, chức danh và vai vế.
4. Làm sạch dữ liệu nhiễu và chuẩn hóa định dạng ký tự.

### 6.3. Nhóm công việc trích xuất thông tin

1. Xác định thực thể cần trích xuất.
2. Trích xuất thông tin cá nhân từ văn bản.
3. Trích xuất quan hệ giữa các cá nhân.
4. Xử lý trường hợp thiếu dữ liệu, dữ liệu mơ hồ hoặc nhiều cách gọi khác nhau cho cùng một người.
5. Gắn độ tin cậy cho từng quan hệ hoặc từng trường dữ liệu nếu cần.

### 6.4. Nhóm công việc mô hình hóa dữ liệu

1. Thiết kế cấu trúc Person, Relationship, Generation, FamilyBranch.
2. Thiết kế lược đồ dữ liệu JSON hoặc cơ sở dữ liệu để lưu thông tin gia phả.
3. Định nghĩa quy tắc ràng buộc: không trùng ID, không tự liên kết, quan hệ hợp lệ, tuổi hợp lý.
4. Chuẩn hóa dữ liệu đầu ra để có thể sinh cây gia phả tự động.

### 6.5. Nhóm công việc xây dựng mô hình tạo cây gia phả

1. Chuyển dữ liệu cấu trúc thành đồ thị quan hệ gia đình.
2. Xác định gốc cây hoặc nhánh tổ tiên.
3. Sắp xếp thành viên theo thế hệ.
4. Hiển thị các quan hệ cha mẹ, vợ chồng, con cái và nhánh phụ.
5. Tạo đầu ra trực quan dưới dạng web hoặc file HTML.

### 6.6. Nhóm công việc giao diện và trải nghiệm người dùng

1. Hiển thị cây gia phả trực quan, dễ đọc.
2. Cho phép xem chi tiết từng cá nhân.
3. Cho phép chỉnh sửa thông tin nếu dữ liệu trích xuất chưa chính xác.
4. Hỗ trợ xuất dữ liệu sang các định dạng như JSON, Excel hoặc HTML.

### 6.7. Nhóm công việc kiểm thử và đánh giá

1. Kiểm tra tính đầy đủ của dữ liệu trích xuất.
2. Kiểm tra tính đúng của các quan hệ gia đình.
3. Đánh giá khả năng dựng cây gia phả với nhiều nhánh và nhiều thế hệ.
4. So sánh kết quả tự động với dữ liệu được chuyên gia hoặc người dùng hiệu chỉnh.

## 7. Kiến trúc đề xuất của hệ thống

Kiến trúc phù hợp cho đề tài này là kiến trúc pipeline nhiều tầng, trong đó mỗi tầng giải quyết một phần riêng của bài toán.

### 7.1. Tầng đầu vào

- Nguồn dữ liệu: văn bản gia phả Hán Nôm, bản phiên âm, bản dịch nghĩa, file văn bản hoặc kết quả OCR.
- Mục tiêu: đưa dữ liệu về dạng text có thể xử lý.

### 7.2. Tầng xử lý ngôn ngữ và trích xuất thông tin

- Nhận văn bản đầu vào.
- Nhận diện các thực thể liên quan đến cá nhân và quan hệ.
- Suy ra cấu trúc dữ liệu ban đầu của từng người và từng mối quan hệ.
- Chuẩn hóa kết quả về schema thống nhất.

### 7.3. Tầng kiểm định và chuẩn hóa dữ liệu

- Kiểm tra dữ liệu thiếu hoặc mâu thuẫn.
- Phát hiện trùng lặp cá nhân.
- Kiểm tra các quan hệ bất hợp lý.
- Gắn nhãn lỗi hoặc gợi ý hiệu chỉnh.

### 7.4. Tầng mô hình hóa quan hệ

- Biểu diễn dữ liệu dưới dạng graph hoặc tree.
- Node là cá nhân.
- Edge là quan hệ gia tộc.
- Hỗ trợ nhiều loại quan hệ khác nhau giữa hai node.

### 7.5. Tầng trực quan hóa và khai thác

- Sinh cây gia phả trực quan.
- Hiển thị theo thế hệ hoặc theo nhánh họ.
- Cho phép tra cứu thông tin chi tiết.
- Cho phép cập nhật thủ công để hoàn thiện dữ liệu.

## 8. Kiến trúc logic chi tiết

Một kiến trúc logic khả thi gồm các module sau:

1. **Input Module**
   - Nhận văn bản đầu vào.
   - Hỗ trợ file text, OCR output hoặc dữ liệu nhập tay.

2. **Preprocessing Module**
   - Làm sạch dữ liệu.
   - Chuẩn hóa định dạng và tách đơn vị thông tin.

3. **Entity Extraction Module**
   - Trích xuất thực thể cá nhân.
   - Trích xuất thuộc tính của cá nhân.

4. **Relationship Extraction Module**
   - Xác định quan hệ cha con, mẹ con, vợ chồng, anh chị em.
   - Gắn quan hệ giữa các thực thể.

5. **Validation Module**
   - Kiểm tra tính hợp lệ của dữ liệu và logic gia phả.

6. **Graph Construction Module**
   - Xây dựng đồ thị gia đình từ dữ liệu cấu trúc.

7. **Visualization Module**
   - Dựng cây gia phả và giao diện hiển thị.

8. **Editing and Export Module**
   - Cho phép người dùng chỉnh sửa và xuất dữ liệu.

## 9. Flow xử lý tổng thể

Flow tổng thể của hệ thống có thể mô tả như sau:

1. Người dùng cung cấp văn bản gia phả Hán Nôm hoặc bản phiên âm.
2. Hệ thống tiếp nhận và tiền xử lý dữ liệu đầu vào.
3. Module trích xuất nhận diện cá nhân và thuộc tính liên quan.
4. Module quan hệ xác định liên kết gia tộc giữa các cá nhân.
5. Dữ liệu được chuẩn hóa thành danh sách người và danh sách quan hệ.
6. Module kiểm định phát hiện lỗi, mâu thuẫn hoặc dữ liệu thiếu.
7. Dữ liệu hợp lệ được chuyển thành đồ thị hoặc cây gia phả.
8. Hệ thống hiển thị cây gia phả trực quan cho người dùng.
9. Người dùng kiểm tra, chỉnh sửa nếu cần.
10. Kết quả cuối cùng được lưu trữ hoặc xuất ra file.

## 10. Flow dữ liệu chi tiết

### 10.1. Input Flow

Văn bản Hán Nôm hoặc văn bản đã phiên âm -> Tiền xử lý -> Văn bản chuẩn hóa

### 10.2. Information Extraction Flow

Văn bản chuẩn hóa -> Trích xuất thực thể -> Trích xuất quan hệ -> Sinh dữ liệu có cấu trúc

### 10.3. Validation Flow

Dữ liệu có cấu trúc -> Kiểm tra schema -> Kiểm tra logic -> Gắn lỗi hoặc xác nhận hợp lệ

### 10.4. Visualization Flow

Dữ liệu hợp lệ -> Tạo graph gia phả -> Sắp xếp theo thế hệ -> Hiển thị cây gia phả -> Xuất kết quả

## 11. Đầu vào và đầu ra của hệ thống

### 11.1. Đầu vào

- Văn bản gia phả Hán Nôm.
- Văn bản phiên âm hoặc dịch nghĩa.
- Dữ liệu hiệu chỉnh thủ công của người dùng.

### 11.2. Đầu ra

- Danh sách cá nhân có cấu trúc.
- Danh sách quan hệ gia tộc.
- Cây gia phả trực quan.
- Báo cáo lỗi dữ liệu hoặc quan hệ bất hợp lý.
- Tệp xuất JSON, HTML, Excel hoặc các định dạng khác.

## 12. Thách thức chính của đề tài

1. Văn bản Hán Nôm có tính đa dạng cao, khó chuẩn hóa.
2. Một người có thể được gọi theo nhiều cách khác nhau.
3. Cấu trúc diễn đạt quan hệ gia đình trong gia phả có thể không thống nhất.
4. Nhiều bản ghi thiếu năm sinh, năm mất hoặc thông tin quan hệ đầy đủ.
5. Việc chuyển từ mô tả ngôn ngữ sang cấu trúc cây yêu cầu xử lý mâu thuẫn dữ liệu.

## 13. Hướng triển khai phù hợp

Để triển khai thực tế, có thể chia thành 3 giai đoạn:

### Giai đoạn 1. Chuẩn hóa dữ liệu và xây dựng schema

- Xây dựng mô hình dữ liệu Person và Relationship.
- Xây dựng bộ dữ liệu mẫu.
- Xây dựng quy tắc kiểm định.

### Giai đoạn 2. Xây dựng pipeline tự động

- Tiền xử lý văn bản.
- Trích xuất thông tin bằng mô hình NLP hoặc AI.
- Sinh dữ liệu cấu trúc và dựng graph.

### Giai đoạn 3. Xây dựng hệ thống hiển thị và hiệu chỉnh

- Hiển thị cây gia phả trên web.
- Hỗ trợ sửa dữ liệu.
- Hỗ trợ lưu trữ và xuất báo cáo.

## 14. Kết luận

Đề tài này hướng tới việc xây dựng một mô hình tự động hóa quá trình chuyển đổi tư liệu gia phả Hán Nôm thành cây gia phả số. Về bản chất, đây là một hệ thống gồm chuỗi xử lý từ tiếp nhận văn bản, trích xuất thông tin, chuẩn hóa dữ liệu, kiểm định logic cho đến trực quan hóa quan hệ gia tộc. Nếu được triển khai tốt, hệ thống không chỉ có giá trị nghiên cứu mà còn có ý nghĩa thực tiễn lớn trong bảo tồn văn hóa, số hóa tư liệu và quản lý thông tin dòng họ.