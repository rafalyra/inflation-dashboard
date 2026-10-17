import { useTranslation } from 'react-i18next';
import { Route, Routes } from 'react-router';
import { Header } from './components/Header';
import { CountryPage } from './pages/Country';
import { LearnPage } from './pages/Learn';
import { MethodologyPage } from './pages/Methodology';
import { NotFoundPage } from './pages/NotFound';
import { OverviewPage } from './pages/Overview';

export function App() {
  const { t } = useTranslation();
  return (
    <>
      <a href="#main" className="skip-link">
        {t('app.skipToContent')}
      </a>
      <Header />
      <main id="main" className="page">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/country/:code" element={<CountryPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}
