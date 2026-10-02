// CI/CD cho family-tree (frontend family-saga-io + backend nlp_family_extractor)
// trên VPS qua Jenkins. Song song với .github/workflows/deploy.yml (GitHub
// Actions SSH vào VPS) — cả 2 cùng chạy đúng logic build-all.sh --up, theo
// yêu cầu người dùng dùng cả 2 cơ chế CI/CD. Domain public:
// https://giapha.kimtudien.com.vn (nginx trên VPS proxy vào container
// family-tree-nginx, publish ở host port 87 — xem infra/docker-compose.yml).
//
// Giả định (Jenkins agent chạy TRÊN chính VPS này, có docker + docker compose
// v2 sẵn — nếu agent là node khác, stage Deploy sẽ không thấy được các
// container mysql/minio/nginx đang chạy sẵn trên VPS, cần đổi sang `agent`
// trỏ đúng node đó).
pipeline {
    agent any
    environment {
        // Link tạm MinIO phải ký với domain công khai (không /minio) — nginx
        // chuyển /family-tree-docs/ vào MinIO giữ nguyên đường dẫn + Host
        // (infra/nginx/conf.d/giapha.kimtudien.com.vn.conf). Mặc định trong
        // compose là localhost:9002 → trình duyệt người dùng không tải được ảnh.
        MINIO_PUBLIC_ENDPOINT = 'https://giapha.kimtudien.com.vn'
    }
    stages {
        stage('Checkout OK') {
            steps {
                echo 'Da checkout family-tree thanh cong!'
            }
        }
        stage('Build & Deploy (backend + frontend)') {
            steps {
                sh './infra/scripts/build-all.sh --up'
            }
        }
        stage('Health check') {
            steps {
                // Jenkins agent chay trong container (docker.sock mount, khong
                // host networking) nen khong thay port host 87 qua localhost —
                // exec thang vao network namespace cua container nginx va goi
                // 127.0.0.1 (khong dung "localhost": busybox wget thu IPv6 ::1
                // truoc, nginx chi listen 0.0.0.0:80 nen bi Connection refused).
                sh '''
                sleep 5
                docker exec family-tree-nginx wget -qO- http://127.0.0.1/health
                '''
            }
        }
    }
}
