'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '../contexts/ThemeContext';
import { AnalysisService } from '../services/api';
import styles from './page.module.css';

export default function Home() {
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const extractRepoName = (url: string): string => {
    const match = url.match(/(?:https?:\/\/)?(?:www\.)?github\.com\/([^/]+\/[^/]+?)(?:\.git)?\/?$/);
    return match ? match[1] : '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsSubmitting(true);
    try {
      console.log('Starting analysis for:', repoUrl);
      const response = await AnalysisService.beginAnalysis(repoUrl);
      console.log('Analysis started with ID:', response.id);
      console.log('Navigating to analysis page...');

      const repoName = extractRepoName(repoUrl);
      // Navigate to analysis page with pipeline ID and repo name after successful start
      router.push(`/analysis?id=${response.id}&repo=${encodeURIComponent(repoName)}`);
    } catch (error) {
      console.error('Failed to start analysis:', error);
      alert(`Failed to start analysis: ${error}`);
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`${styles.container} ${theme === 'dark' ? styles.darkMode : ''}`}>
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

      <div className={styles.content}>
        <h1 className={`${styles.title} ${styles.appTitle}`}>
          RepoStory
        </h1>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputContainer}>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="Enter GitHub repository URL..."
              className={styles.input}
            />
            <button
              type="submit"
              className={styles.submitButton}
              disabled={isSubmitting}
            >
              <svg
                className={styles.arrow}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
