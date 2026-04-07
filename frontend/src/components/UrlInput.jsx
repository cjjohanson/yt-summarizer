import React, { useState } from 'react';

const YT_REGEX = /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?v=|live\/|shorts\/)|youtu\.be\/)[A-Za-z0-9_-]+/;

const TRANSCRIBER_OPTIONS = [
  { value: 'groq', label: 'Groq (default)' },
  { value: 'openai', label: 'OpenAI Whisper' },
  { value: 'local', label: 'Local whisper-server' },
];

export default function UrlInput({ onSubmit, loading }) {
  const [url, setUrl] = useState('');
  const [transcriber, setTranscriber] = useState('groq');
  const [error, setError] = useState('');

  const isValid = YT_REGEX.test(url);

  function handleSubmit(e) {
    e.preventDefault();
    if (!url.trim()) return;
    if (!isValid) {
      setError('Please enter a valid YouTube URL');
      return;
    }
    setError('');
    onSubmit(url.trim(), { transcriber });
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="url-input-container">
        <input
          type="text"
          className={`url-input ${url && !isValid ? 'invalid' : ''}`}
          placeholder="Paste a YouTube URL..."
          value={url}
          onChange={(e) => { setUrl(e.target.value); setError(''); }}
          disabled={loading}
        />
        <select
          className="transcriber-select"
          value={transcriber}
          onChange={(e) => setTranscriber(e.target.value)}
          disabled={loading}
        >
          {TRANSCRIBER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !url.trim()}
        >
          {loading ? 'Submitting...' : 'Summarize'}
        </button>
      </div>
      {error && <div className="url-input-error">{error}</div>}
    </form>
  );
}
