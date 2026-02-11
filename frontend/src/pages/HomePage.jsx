import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import UrlInput from '../components/UrlInput';
import VideoCard from '../components/VideoCard';
import { submitVideo, listVideos } from '../api';

export default function HomePage() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listVideos({ limit: 12 })
      .then((data) => setVideos(data.videos))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(url, opts = {}) {
    setSubmitting(true);
    setError('');
    try {
      const video = await submitVideo(url, opts);
      if (video.status === 'completed') {
        navigate(`/video/${video.id}`);
      } else {
        navigate(`/video/${video.id}/processing`);
      }
    } catch (err) {
      setError(err.message || 'Failed to submit video');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="hero">
        <h1>YouTube Video Summarizer</h1>
        <p>Paste a YouTube URL and get a comprehensive summary in minutes.</p>
        <UrlInput onSubmit={handleSubmit} loading={submitting} />
        {error && <div className="url-input-error" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      <h2 className="section-title">Recent Videos</h2>

      {loading ? (
        <div className="video-grid">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton skeleton-card" />
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="empty-state">
          <p>No videos yet.</p>
          <p>Paste a YouTube URL above to get started.</p>
        </div>
      ) : (
        <div className="video-grid">
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
