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
                sh '''
                sleep 5
                curl -fsS http://localhost:87/health
                '''
            }
        }
    }
}
