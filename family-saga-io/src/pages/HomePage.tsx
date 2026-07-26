import { useEffect } from 'react';
import { Button, Card } from 'antd';
import { BookOutlined, TeamOutlined, BranchesOutlined, SafetyOutlined, InboxOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from 'next-themes';
import heroBg from '@/assets/hero-bg.jpg';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';

const HomePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const { isAuthenticated, isAdmin, logout } = useAuth();
  const { resolvedTheme, systemTheme } = useTheme();
  const isDark = (resolvedTheme ?? systemTheme) === 'dark';
  const footerToggleVariant = isDark ? 'default' : 'on-dark';

  useEffect(() => {
    if (location.hash) {
      const id = location.hash.replace('#', '');
      setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [location.hash]);

  const features = [
    { icon: BranchesOutlined, title: t('home.f1Title'), desc: t('home.f1Desc') },
    { icon: TeamOutlined, title: t('home.f2Title'), desc: t('home.f2Desc') },
    { icon: BookOutlined, title: t('home.f3Title'), desc: t('home.f3Desc') },
    { icon: InboxOutlined, title: t('home.f4Title'), desc: t('home.f4Desc') },
    { icon: SafetyOutlined, title: t('home.f5Title'), desc: t('home.f5Desc') },
  ];

  return (
    <div className="min-h-screen bg-background">
      <section className="relative min-h-[480px] md:h-[600px] flex items-center justify-center overflow-hidden">
        <img
          src={heroBg}
          alt="Gia phả truyền thống"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="hero-overlay absolute inset-0" />
        <div className="relative z-10 text-center max-w-3xl px-4 sm:px-6">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-bold text-white mb-4 md:mb-6 leading-tight">
            {t('home.heroTitle')}
          </h1>
          <p className="text-lg sm:text-xl md:text-2xl text-white/90 font-body mb-6 md:mb-8">
            {t('home.heroSubtitle')}
          </p>
          <div className="flex gap-3 sm:gap-4 justify-center flex-wrap">
            <Button
              type="primary"
              size="large"
              className="!h-12 !px-8"
              onClick={() =>
                navigate(isAuthenticated ? "/user/documents/new" : "/login", {
                  state: { from: "/user/documents/new" },
                })
              }
            >
              {t("home.btnStartFlow", { defaultValue: "Bắt đầu quy trình" })}
            </Button>
            <Button
              type="default"
              size="large"
              className="hero-btn-solid-light !h-12 !px-8"
              styles={{
                root: {
                  background: "#ffffff",
                  borderColor: "#ffffff",
                  color: "hsl(160, 10%, 12%)",
                },
              }}
              onClick={() => navigate("/gia-pha")}
            >
              {t("home.btnViewSample")}
            </Button>
          </div>
          <p className="mt-5 text-white/80 text-sm flex flex-wrap justify-center gap-x-4 gap-y-1">
            <button
              type="button"
              className="underline hover:text-white bg-transparent border-0 cursor-pointer"
              onClick={() => navigate("/huong-dan")}
            >
              {t("nav.guide")}
            </button>
            {!isAuthenticated ? (
              <button
                type="button"
                className="underline hover:text-white bg-transparent border-0 cursor-pointer"
                onClick={() => navigate("/login")}
              >
                {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="underline hover:text-white bg-transparent border-0 cursor-pointer"
                  onClick={() => navigate("/user/dashboard")}
                >
                  {t("pages.userDashboard.title", { defaultValue: "Tổng quan" })}
                </button>
                {isAdmin && (
                  <button
                    type="button"
                    className="underline hover:text-white bg-transparent border-0 cursor-pointer"
                    onClick={() => navigate("/admin/dashboard")}
                  >
                    {t("admin.panelTitle", { defaultValue: "Admin" })}
                  </button>
                )}
                <button
                  type="button"
                  className="underline hover:text-white bg-transparent border-0 cursor-pointer"
                  onClick={logout}
                >
                  {t("auth.logout", { defaultValue: "Đăng xuất" })}
                </button>
              </>
            )}
          </p>
        </div>
      </section>

      <div className="section-divider mx-auto max-w-4xl my-0" />

      <section id="features" className="py-16 md:py-20 px-4 sm:px-6 scroll-mt-20">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-display font-bold text-center text-foreground mb-4">
            {t('home.featuresTitle')}
          </h2>
          <p className="text-center text-muted-foreground mb-10 md:mb-12 max-w-2xl mx-auto text-base sm:text-lg">
            {t('home.featuresSubtitle')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 sm:gap-6">
            {features.map((f, i) => {
              const Icon = f.icon;
              return (
                <Card
                  key={i}
                  hoverable
                  className="text-center border-2 transition-all duration-300 bg-card border-border hover:border-primary/60"
                  styles={{ body: { padding: 24 } }}
                >
                  <Icon className="text-3xl text-primary mb-4" />
                  <h3 className="text-lg font-display font-semibold text-foreground mb-2">{f.title}</h3>
                  <p className="text-muted-foreground text-sm">{f.desc}</p>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      <section className="brand-gradient py-12 md:py-16 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 text-center">
          {[
            { num: '10,000+', label: t('home.stat1') },
            { num: '150,000+', label: t('home.stat2') },
            { num: '500+', label: t('home.stat3') },
            { num: '99.9%', label: t('home.stat4') },
          ].map((s, i) => (
            <div key={i}>
              <div className="text-2xl sm:text-3xl md:text-4xl font-display font-bold">{s.num}</div>
              <div className="opacity-90 mt-1 text-sm sm:text-base">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 md:py-20 px-4 sm:px-6 text-center">
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
          {t('home.ctaTitle')}
        </h2>
        <p className="text-muted-foreground text-base sm:text-lg mb-6 md:mb-8 max-w-xl mx-auto">
          {t('home.ctaSubtitle')}
        </p>
        <Button
          type="primary"
          size="large"
          className="!h-[52px] !px-10 !text-base"
          onClick={() =>
            navigate(isAuthenticated ? "/user/documents/new" : "/register")
          }
        >
          {t("home.btnStartFlow", { defaultValue: "Bắt đầu quy trình" })}
        </Button>
      </section>

      <section id="about" className="py-16 md:py-20 px-4 sm:px-6 bg-background scroll-mt-20">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-display font-bold text-foreground mb-4">
            {t('home.aboutTitle', { defaultValue: 'Về chúng tôi' })}
          </h2>
          <p className="text-muted-foreground text-base sm:text-lg leading-relaxed">
            {t('home.aboutDesc', {
              defaultValue:
                'HCMUS Family Tree là nền tảng số hóa gia phả, giúp các dòng họ Việt Nam lưu giữ tư liệu Hán-Nôm, xây dựng cây phả hệ trực quan và chia sẻ với thế hệ kế tiếp.',
            })}
          </p>
        </div>
      </section>

      <footer className="site-footer border-t border-border py-8 px-4 sm:px-6 text-center">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <p className="text-sm opacity-80">{t('home.footer')}</p>
          <div className="flex items-center gap-4">
            <LanguageSwitcher />
            <ThemeToggle variant={footerToggleVariant} />
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
