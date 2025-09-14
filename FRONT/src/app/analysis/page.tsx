'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTheme } from '../../contexts/ThemeContext';
import { AnalysisService, SSEEvent } from '../../services/api';
import Timeline, { Milestone } from '../../components/Timeline';
import styles from './page.module.css';

export default function Analysis() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [repoName, setRepoName] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const pipelineId = searchParams.get('id');
    const repo = searchParams.get('repo');

    if (!pipelineId) {
      console.error('No pipeline ID provided');
      router.push('/');
      return;
    }

    if (repo) {
      setRepoName(decodeURIComponent(repo));
    }

    console.log('Starting SSE subscription for pipeline:', pipelineId);

    // Subscribe to SSE events
    const eventSource = AnalysisService.subscribeToAnalysis(
      pipelineId,
      (event) => {
        console.log('Processing event:', event);
        setEvents(prev => [...prev, event]);

        // Check for milestone_start event (create placeholder card)
        if (event.type === 'milestone_start' && event.payload) {
          const placeholder: Milestone = {
            title: 'Processing milestone...',
            summary: `Analyzing ${event.payload.messages?.length || 0} commits...`,
            files: []
          };
          setMilestones(prev => [...prev, placeholder]);
        }

        // Check for milestone_analysis event (update with final processed data)
        if (event.type === 'milestone_analysis' && event.payload) {
          setMilestones(prev => {
            const updated = [...prev];
            // Find the last placeholder and update it
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].title === 'Processing milestone...') {
                updated[i] = {
                  title: event.payload.title || 'Milestone',
                  summary: event.payload.summary || '',
                  files: event.payload.most_important_changes || []
                };
                break;
              }
            }
            return updated;
          });
        }

        // Check for end event
        if (event.type === 'end') {
          console.log('Analysis complete:', event.payload);
          setIsComplete(true);
          eventSource.close();
        }
      },
      (error) => {
        console.error('SSE error:', error);
      }
    );

    eventSourceRef.current = eventSource;

    // Cleanup on unmount
    return () => {
      console.log('Closing SSE connection');
      eventSource.close();
    };
  }, [searchParams, router]);

  const handleNewAnalysis = () => {
    router.push('/');
  };

  return (
    <div className={`${styles.container} ${theme === 'dark' ? styles.darkMode : ''}`}>
      <nav className={styles.navbar}>
        <div className={styles.navbarContent}>
          <div className={styles.navbarInner}>
            <div className={styles.titleSection}>
              <h1 className={styles.projectTitle}>
                <a className={styles.appTitle} href="/">RepoStory</a> {repoName ? `| ${repoName}` : ''}
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
        {milestones.length > 0 ? (
          <Timeline milestones={milestones} theme={theme} />
        ) : (
          <div className={styles.resultsContainer}>
            <h2 className={styles.resultsTitle}>
              {isComplete ? 'No milestones found' : 'Analyzing repository...'}
            </h2>
            <p className={styles.resultsText}>
              {isComplete ? 'The analysis completed but no milestones were generated.' : 'Processing commit history and generating milestone summaries...'}
            </p>
            {!isComplete && (
              <div className={styles.loadingIndicator}>
                <div className={styles.spinner}></div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}