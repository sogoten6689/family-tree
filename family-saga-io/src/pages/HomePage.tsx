import { Button, Card } from 'antd';
import { BookOutlined, TeamOutlined, BranchesOutlined, SafetyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import heroBg from '@/assets/hero-bg.jpg';

const features = [
  {
    icon: <BranchesOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
    title: 'Cây gia phả trực quan',
    desc: 'Hiển thị mối quan hệ huyết thống qua nhiều thế hệ với giao diện đẹp mắt, dễ hiểu.',
  },
  {
    icon: <TeamOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
    title: 'Quản lý thành viên',
    desc: 'Thêm, sửa thông tin từng thành viên trong gia đình với đầy đủ tiểu sử.',
  },
  {
    icon: <BookOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
    title: 'Lưu trữ lịch sử',
    desc: 'Ghi chép và bảo tồn những câu chuyện, sự kiện quan trọng của dòng họ.',
  },
  {
    icon: <SafetyOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
    title: 'Bảo mật & Chia sẻ',
    desc: 'Dữ liệu được bảo mật an toàn, dễ dàng chia sẻ với các thành viên trong gia đình.',
  },
];

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative h-[600px] flex items-center justify-center overflow-hidden">
        <img src={heroBg} alt="Gia phả truyền thống" className="absolute inset-0 w-full h-full object-cover" />
        <div className="hero-overlay absolute inset-0" />
        <div className="relative z-10 text-center max-w-3xl px-6">
          <h1 className="text-5xl md:text-6xl font-display font-bold text-parchment mb-6 leading-tight">
            Gia Phả Việt
          </h1>
          <p className="text-xl md:text-2xl text-gold-light font-body mb-8">
            Gìn giữ và tôn vinh truyền thống dòng họ — Kết nối quá khứ, hiện tại và tương lai
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Button
              type="primary"
              size="large"
              onClick={() => navigate('/family-tree')}
              style={{
                background: 'hsl(36, 70%, 42%)',
                borderColor: 'hsl(36, 70%, 42%)',
                height: 48,
                fontSize: 16,
                fontFamily: 'var(--font-body)',
                paddingInline: 32,
              }}
            >
              Xem Gia Phả Mẫu
            </Button>
            <Button
              size="large"
              ghost
              style={{
                borderColor: 'hsl(39, 60%, 70%)',
                color: 'hsl(39, 60%, 70%)',
                height: 48,
                fontSize: 16,
                fontFamily: 'var(--font-body)',
                paddingInline: 32,
              }}
            >
              Tìm Hiểu Thêm
            </Button>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider mx-auto max-w-4xl my-0" />

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-display font-bold text-center text-foreground mb-4">
            Tính Năng Nổi Bật
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto text-lg">
            Công cụ hiện đại giúp bạn xây dựng và lưu giữ gia phả dòng họ một cách dễ dàng
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => (
              <Card
                key={i}
                hoverable
                className="text-center border-2 transition-all duration-300"
                style={{
                  borderColor: 'hsl(36, 30%, 80%)',
                  background: 'hsl(39, 40%, 93%)',
                }}
                styles={{ body: { padding: 32 } }}
              >
                <div className="mb-4">{f.icon}</div>
                <h3 className="text-lg font-display font-semibold text-foreground mb-2">{f.title}</h3>
                <p className="text-muted-foreground text-sm">{f.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="gold-gradient py-16 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { num: '10,000+', label: 'Gia phả đã tạo' },
            { num: '150,000+', label: 'Thành viên' },
            { num: '500+', label: 'Dòng họ' },
            { num: '99.9%', label: 'Uptime' },
          ].map((s, i) => (
            <div key={i}>
              <div className="text-3xl md:text-4xl font-display font-bold text-parchment">{s.num}</div>
              <div className="text-parchment/80 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 text-center">
        <h2 className="text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
          Bắt Đầu Xây Dựng Gia Phả
        </h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto">
          Chỉ vài bước đơn giản, bạn đã có thể tạo cây gia phả hoàn chỉnh cho dòng họ mình.
        </p>
        <Button
          type="primary"
          size="large"
          onClick={() => navigate('/family-tree')}
          style={{
            background: 'hsl(0, 45%, 35%)',
            borderColor: 'hsl(0, 45%, 35%)',
            height: 52,
            fontSize: 18,
            fontFamily: 'var(--font-body)',
            paddingInline: 40,
          }}
        >
          Tạo Gia Phả Ngay
        </Button>
      </section>

      {/* Footer */}
      <footer className="bg-wood py-8 px-6 text-center">
        <p className="text-parchment/70 text-sm">
          © 2026 Gia Phả Việt — Gìn giữ truyền thống, kết nối thế hệ
        </p>
      </footer>
    </div>
  );
};

export default HomePage;
