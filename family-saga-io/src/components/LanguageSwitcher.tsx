import { useTranslation } from 'react-i18next';
import i18n from '@/i18n';

const LanguageSwitcher = () => {
  const { i18n: i18nInstance } = useTranslation();
  const currentLang = i18nInstance.language;

  const toggle = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('lang', lang);
  };

  return (
    <div
      className="flex items-center gap-1 rounded-lg border px-1 py-1"
      style={{ borderColor: 'hsl(var(--border))', background: 'hsl(var(--card))' }}
    >
      <button
        onClick={() => toggle('vi')}
        className="rounded px-2 py-0.5 text-sm font-medium transition-all"
        style={{
          background: currentLang === 'vi' ? 'hsl(var(--primary))' : 'transparent',
          color: currentLang === 'vi' ? 'hsl(var(--primary-foreground))' : 'hsl(var(--foreground))',
        }}
      >
        VI
      </button>
      <button
        onClick={() => toggle('en')}
        className="rounded px-2 py-0.5 text-sm font-medium transition-all"
        style={{
          background: currentLang === 'en' ? 'hsl(var(--primary))' : 'transparent',
          color: currentLang === 'en' ? 'hsl(var(--primary-foreground))' : 'hsl(var(--foreground))',
        }}
      >
        EN
      </button>
    </div>
  );
};

export default LanguageSwitcher;
