import React from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from './StatusBadge';

function formatDuration(seconds) {
  if (!seconds) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function VideoCard({ video }) {
  const thumbUrl = video.thumbnail_url
    || `https://img.youtube.com/vi/${video.youtube_id}/mqdefault.jpg`;

  const link = video.status === 'completed'
    ? `/video/${video.id}`
    : `/video/${video.id}/processing`;

  return (
    <Link to={link} className="video-card">
      <img
        className="video-card-thumb"
        src={thumbUrl}
        alt={video.title || 'Video thumbnail'}
        loading="lazy"
      />
      <div className="video-card-body">
        <div className="video-card-title">
          {video.title || 'Processing...'}
        </div>
        <div className="video-card-meta">
          {video.channel && <span>{video.channel}</span>}
          {video.duration_seconds > 0 && (
            <span>{formatDuration(video.duration_seconds)}</span>
          )}
          <StatusBadge status={video.status} />
        </div>
      </div>
    </Link>
  );
}
