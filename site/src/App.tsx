import { useEffect, useState } from 'react';
import { LearnPage } from './pages/LearnPage';
import { IntroPage } from './pages/IntroPage';
import './styles.css';

type Page = 'learn' | 'intro';

function currentPage(): Page {
  switch (window.location.hash) {
    case '':
    case '#intro':
      return 'intro';
    default:
      return 'learn';
  }
}

export default function App() {
  const [page, setPage] = useState(currentPage);

  useEffect(() => {
    const navigate = () => {
      const next = currentPage();
      if (next === 'learn' && window.location.hash !== '#learn') {
        window.history.replaceState(null, '', '/#learn');
      }
      setPage(next);
    };
    navigate();
    window.addEventListener('hashchange', navigate);
    return () => window.removeEventListener('hashchange', navigate);
  }, []);

  return (
    <main className={page === 'intro' ? 'workspace workspace-learn workspace-home' : 'workspace workspace-learn'}>
      <header className="workspace-header">
        <h1><a className="site-wordmark" href="#intro">Decision Models</a></h1>
        <nav className="main-nav" aria-label="Main navigation">
          <a href="#intro" aria-current={page === 'intro' ? 'page' : undefined}>Home</a>
          <a href="#learn" aria-current={page === 'learn' ? 'page' : undefined}>Learn</a>
        </nav>
      </header>
      {page === 'learn' ? <LearnPage /> : <IntroPage />}
    </main>
  );
}