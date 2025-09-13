'use client';

import { useRouter } from 'next/navigation';
import { useTheme } from '../../contexts/ThemeContext';
import styles from './page.module.css';

export default function Analysis() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const handleNewAnalysis = () => {
    router.push('/');
  };

  return (
    <div className={`${styles.container} ${theme === 'dark' ? styles.darkMode : ''}`}>
      <nav className={styles.navbar}>
        <div className={styles.navbarContent}>
          <div className={styles.navbarInner}>
            <div>
              <h1 className={styles.projectTitle}>
                ProjectName Here
              </h1>
            </div>
            <div className={styles.navActions}>
              <button
                onClick={toggleTheme}
                className={styles.themeToggle}
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <svg className={styles.themeIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className={styles.themeIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button
                onClick={handleNewAnalysis}
                className={styles.newAnalysisButton}
              >
                New Analysis
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className={styles.main}>
        <div className={styles.resultsContainer}>
          <h2 className={styles.resultsTitle}>
            Analysis Results
          </h2>
          <p className={styles.resultsText}>
            Analysis results will be displayed here...
          </p>
        </div>
      </main>
    </div>
  );
}