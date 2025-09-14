'use client';

import { useState } from 'react';
import styles from './Timeline.module.css';

export interface Milestone {
  title: string;
  summary: string;
  files: string[];
  timestamp?: string;
}

interface TimelineProps {
  milestones: Milestone[];
  theme?: 'light' | 'dark';
}

const renderSummaryWithCodeBlocks = (text: string) => {
  // Split text by backticks, keeping the delimiters
  const parts = text.split(/(`[^`]+`)/);

  return parts.map((part, index) => {
    // Check if this part is surrounded by backticks
    if (part.startsWith('`') && part.endsWith('`')) {
      // Remove the backticks and render as code
      const codeText = part.slice(1, -1);
      return (
        <code key={index} className={styles.inlineCode}>
          {codeText}
        </code>
      );
    }
    // Regular text
    return part;
  });
};

export default function Timeline({ milestones, theme = 'light' }: TimelineProps) {
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());

  const toggleCard = (index: number) => {
    setExpandedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const isLoading = (milestone: Milestone) => {
    return milestone.title === 'Processing milestone...';
  };

  return (
    <div className={`${styles.timeline} ${theme === 'dark' ? styles.dark : ''}`}>
      <div className={styles.timelineLine} />

      {milestones.map((milestone, index) => (
        <div
          key={index}
          className={`${styles.timelineItem} ${
            index % 2 === 0 ? styles.left : styles.right
          }`}
        >
          <div className={styles.timelineDot} />

          <div className={`${styles.timelineCard} ${isLoading(milestone) ? styles.loadingCard : ''}`}>
            <h3 className={styles.cardTitle}>{milestone.title}</h3>
            <div className={styles.cardSummary}>
              {renderSummaryWithCodeBlocks(milestone.summary)}
            </div>

            {milestone.files.length > 0 && (
              <div className={styles.filesSection}>
                <button
                  className={styles.filesToggle}
                  onClick={() => toggleCard(index)}
                  aria-expanded={expandedCards.has(index)}
                >
                  <span className={styles.filesLabel}>
                    {milestone.files.length} key file{milestone.files.length !== 1 ? 's' : ''} 
                  </span>
                  <svg
                    className={`${styles.chevron} ${
                      expandedCards.has(index) ? styles.chevronUp : ''
                    }`}
                    width="12"
                    height="8"
                    viewBox="0 0 12 8"
                    fill="none"
                  >
                    <path
                      d="M1 1.5L6 6.5L11 1.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>

                {expandedCards.has(index) && (
                  <ul className={styles.filesList}>
                    {milestone.files.map((file, fileIndex) => (
                      <li key={fileIndex} className={styles.fileName}>
                        {file}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}