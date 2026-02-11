import React from 'react';

const LABELS = {
  pending: 'Pending',
  downloading: 'Downloading',
  transcribing: 'Transcribing',
  summarizing: 'Summarizing',
  completed: 'Completed',
  failed: 'Failed',
};

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge ${status}`}>
      {LABELS[status] || status}
    </span>
  );
}
