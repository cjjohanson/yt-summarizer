import React from 'react';
import ReactMarkdown from 'react-markdown';

export default function SummaryView({ content }) {
  if (!content) {
    return <div className="empty-state"><p>No summary available.</p></div>;
  }

  return (
    <div className="summary-content">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
