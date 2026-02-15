import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import SummaryView from '../components/SummaryView';
import StatusBadge from '../components/StatusBadge';
import { getVideo, deleteVideo } from '../api';
import { formatDuration, formatTimeSaved } from '../utils/format';

const TABS = [
  { key: 'executive', label: 'Executive Summary' },
  { key: 'detailed', label: 'Detailed Summary' },
  { key: 'transcript', label: 'Full Transcript' },
];

export default function VideoPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('executive');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    getVideo(id)
      .then(setVideo)
      .catch(() => navigate('/'))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDelete() {
    if (!window.confirm('Delete this video and all its summaries?')) return;
    setDeleting(true);
    try {
      await deleteVideo(id);
      navigate('/');
    } catch {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div>
        <div className="skeleton" style={{ height: 200, marginBottom: 24 }} />
        <div className="skeleton skeleton-text wide" />
        <div className="skeleton skeleton-text medium" />
      </div>
    );
  }

  if (!video) return null;

  const thumbUrl = video.thumbnail_url
    || `https://img.youtube.com/vi/${video.youtube_id}/maxresdefault.jpg`;

  return (
    <div>
      <div className="video-detail-header">
        <div className="video-detail-thumb">
          <img src={thumbUrl} alt={video.title} />
        </div>
        <div className="video-detail-info">
          <h1>{video.title}</h1>
          <div className="video-detail-meta">
            <span>{video.channel}</span>
            {video.duration_seconds > 0 && (
              <span>Duration: {formatDuration(video.duration_seconds)}</span>
            )}
            {video.status === 'completed' && video.duration_seconds > 0 && (
              <span className="time-saved-inline">You saved {formatTimeSaved(video.duration_seconds)}</span>
            )}
            {video.upload_date && <span>Uploaded: {video.upload_date}</span>}
            <span>
              <a href={video.youtube_url} target="_blank" rel="noopener noreferrer">
                Watch on YouTube
              </a>
            </span>
          </div>
          <StatusBadge status={video.status} />
          <div className="video-detail-actions">
            <button
              className="btn btn-danger btn-sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      </div>

      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'executive' && (
        <SummaryView content={video.summaries?.executive?.content} />
      )}
      {activeTab === 'detailed' && (
        <SummaryView content={video.summaries?.detailed?.content} />
      )}
      {activeTab === 'transcript' && (
        <div className="transcript-content">
          {video.transcript?.content || 'No transcript available.'}
        </div>
      )}

      <div className="meta-footer">
        {video.transcriber_used && <span>Transcriber: {video.transcriber_used}</span>}
        {video.llm_model_used && <span>Model: {video.llm_model_used}</span>}
        {video.transcript?.word_count > 0 && (
          <span>Transcript: {video.transcript.word_count.toLocaleString()} words</span>
        )}
        {video.summaries?.detailed?.word_count > 0 && (
          <span>Detailed: {video.summaries.detailed.word_count.toLocaleString()} words</span>
        )}
        {video.completed_at && <span>Processed: {new Date(video.completed_at).toLocaleDateString()}</span>}
      </div>
    </div>
  );
}
