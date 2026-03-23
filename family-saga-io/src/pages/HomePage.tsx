import { Button, Card } from 'antd';
import { BookOutlined, TeamOutlined, BranchesOutlined, SafetyOutlined, InboxOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import heroBg from '@/assets/hero-bg.jpg';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

const HomePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const features = [
    {
      icon: <BranchesOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
      title: t('home.f1Title'),
      desc: t('home.f1Desc'),
    },
    {
      icon: <TeamOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
      title: t('home.f2Title'),
      desc: t('home.f2Desc'),
    },
    {
      icon: <BookOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
      title: t('home.f3Title'),
      desc: t('home.f3Desc'),
    },
    {
      icon: <InboxOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
      title: t('home.f4Title'),
      desc: t('home.f4Desc'),
    },
    {
      icon: <SafetyOutlined className="text-3xl" style={{ color: 'hsl(36, 70%, 42%)' }} />,
      title: t('home.f5Title'),
      desc: t('home.f5Desc'),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative h-[600px] flex items-center justify-center overflow-hidden">
        <img src={heroBg} alt="Gia phả truyền thống" className="absolute inset-0 w-full h-full object-cover" />
        <div className="hero-overlay absolute inset-0" />
        <div className="relative z-10 text-center max-w-3xl px-6">
          <h1 className="text-5xl md:text-6xl font-display font-bold text-parchment mb-6 leading-tight">
            {t('home.heroTitle')}
          </h1>
          <p className="text-xl md:text-2xl text-gold-light font-body mb-8">
            {t('home.heroSubtitle')}
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
                {t('home.btnViewSample')}
            </Button>
            <Button
              size="large"
              onClick={() => navigate('/document-reader')}
              style={{
                background: 'hsl(39, 50%, 96%)',
                borderColor: 'hsl(39, 50%, 96%)',
                color: 'hsl(20, 40%, 25%)',
                height: 48,
                fontSize: 16,
                fontFamily: 'var(--font-body)',
                paddingInline: 32,
              }}
            >
                {t('home.btnOpenDoc')}
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
            {t('home.featuresTitle')}
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto text-lg">
            {t('home.featuresSubtitle')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
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
            { num: '10,000+', label: t('home.stat1') },
            { num: '150,000+', label: t('home.stat2') },
            { num: '500+', label: t('home.stat3') },
            { num: '99.9%', label: t('home.stat4') },
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
          {t('home.ctaTitle')}
        </h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto">
          {t('home.ctaSubtitle')}
        </p>
        <Button
          type="primary"
          size="large"
          onClick={() => navigate('/document-reader')}
          style={{
            background: 'hsl(0, 45%, 35%)',
            borderColor: 'hsl(0, 45%, 35%)',
            height: 52,
            fontSize: 18,
            fontFamily: 'var(--font-body)',
            paddingInline: 40,
          }}
        >
          {t('home.ctaBtn')}
        </Button>
      </section>

      {/* Footer */}
      <footer className="bg-wood py-8 px-6 text-center">
        <div className="flex items-center justify-center gap-4">
          <p className="text-parchment/70 text-sm">{t('home.footer')}</p>
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
