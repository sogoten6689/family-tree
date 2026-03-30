Một người có thể có nhiều loại quan hệ (cha/mẹ, vợ/chồng, anh/chị/em).

Quan hệ vợ/chồng là quan hệ đối xứng

Có thể có nhiều cạnh giữa cùng 2 người với ý nghĩa khác nhau.

Node: mỗi Person là một node, unique = id.
Edge mỗi Relationship là một cạnh để định nghĩa quan hệ
{"from_id":"P001","to_id":"P003","type":"parent_of"} nghĩa là cạnh P001 -> P003.

Logic tạm hiểu

kiểm tra node: id không trùng, dữ liệu người hợp lệ.
Kiểm tra edge: from_id/to_id phải tồn tại trong danh sách node, type hợp lệ, không self-loop, confidence trong [0,1].
Kiểm tra logic theo loại cạnh: ví dụ parent_of phải có chênh lệch tuổi hợp lý; spouse_of không bị trùng cặp (A-B và B-A).

# run
cd view-family-tree
run pip install -r requirements.txt
run python -m src.main
