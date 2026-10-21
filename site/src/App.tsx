import { useEffect, useState } from 'react';
import { LearnPage } from './pages/LearnPage';
import { IntroPage } from './pages/IntroPage';
import { RecordingsPage } from './pages/RecordingsPage';
import './recordings/recordings.css';
import './styles.css';

type Page = 'learn' | 'intro' | 'recordings';

function currentPage(): Page {
  const hash = window.location.hash;
  if (hash === '#recordings' || hash.startsWith('#recordings/')) return 'recordings';
  switch (hash) {
    case '':
    case '#intro':
      return 'intro';
    default:
      return 'learn';
  }
}

function recordingsRoute(): { scenario?: string; runId?: string } {
  const [, scenario, runId] = window.location.hash.slice(1).split('/');
  return { scenario: scenario || undefined, runId: runId || undefined };
}

export default function App() {
  const [page, setPage] = useState(currentPage);
  const [, setHash] = useState(window.location.hash);

  useEffect(() => {
    const navigate = () => {
      const next = currentPage();
      if (next === 'learn' && window.location.hash !== '#learn') {
        window.history.replaceState(null, '', '/#learn');
      }
      setPage(next);
      setHash(window.location.hash);
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
          <a href="#recordings" aria-current={page === 'recordings' ? 'page' : undefined}>Recorded runs</a>
        </nav>
      </header>
      {page === 'learn' ? <LearnPage /> : page === 'recordings' ? <RecordingsPage {...recordingsRoute()} /> : <IntroPage />}
    </main>
  );
}