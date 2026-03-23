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
    <div className="flex items-center gap-1 rounded-lg border px-1 py-1" style={{ borderColor: 'hsl(36, 30%, 80%)' }}>
      <button
        onClick={() => toggle('vi')}
        className="rounded px-2 py-0.5 text-sm font-medium transition-all"
        style={{
          background: currentLang === 'vi' ? 'hsl(36, 70%, 42%)' : 'transparent',
          color: currentLang === 'vi' ? 'hsl(39, 50%, 96%)' : 'hsl(20, 30%, 15%)',
        }}
      >
        VI
      </button>
      <button
        onClick={() => toggle('en')}
        className="rounded px-2 py-0.5 text-sm font-medium transition-all"
        style={{
          background: currentLang === 'en' ? 'hsl(36, 70%, 42%)' : 'transparent',
          color: currentLang === 'en' ? 'hsl(39, 50%, 96%)' : 'hsl(20, 30%, 15%)',
        }}
      >
        EN
      </button>
    </div>
  );
};

export default LanguageSwitcher;
