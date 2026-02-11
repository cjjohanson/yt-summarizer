import React, { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import VideoCard from '../components/VideoCard';
import { listVideos, searchVideos } from '../api';

const FILTERS = [
  { key: null, label: 'All' },
  { key: 'completed', label: 'Completed' },
  { key: 'pending,downloading,transcribing,summarizing', label: 'Processing' },
  { key: 'failed', label: 'Failed' },
];

export default function LibraryPage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    setLoading(true);

    if (query.trim()) {
      searchVideos(query)
        .then((data) => {
          // Search results come back as { results: [...] }
          // Map them to match the video shape for VideoCard
          const mapped = data.results.map((r) => ({
            id: r.video_id,
            youtube_id: r.youtube_id,
            title: r.title,
            channel: r.channel,
            thumbnail_url: r.thumbnail_url,
            status: r.status,
          }));
          setVideos(mapped);
        })
        .catch(() => setVideos([]))
        .finally(() => setLoading(false));
    } else {
      // For "Processing" filter, we filter client-side since the API only takes one status
      const statusParam = activeFilter && !activeFilter.includes(',') ? activeFilter : null;
      listVideos({ status: statusParam, limit: 200 })
        .then((data) => {
          let result = data.videos;
          if (activeFilter && activeFilter.includes(',')) {
            const statuses = activeFilter.split(',');
            result = result.filter((v) => statuses.includes(v.status));
          }
          setVideos(result);
        })
        .catch(() => setVideos([]))
        .finally(() => setLoading(false));
    }
  }, [query, activeFilter]);

  return (
    <div>
      <h1 className="section-title" style={{ marginBottom: 16 }}>Library</h1>

      <SearchBar value={query} onChange={setQuery} placeholder="Search transcripts and summaries..." />

      {!query && (
        <div className="filter-bar">
          {FILTERS.map((f) => (
            <button
              key={f.label}
              className={`filter-btn ${activeFilter === f.key ? 'active' : ''}`}
              onClick={() => setActiveFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="video-grid">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton skeleton-card" />
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="empty-state">
          {query ? (
            <p>No results found for "{query}".</p>
          ) : (
            <>
              <p>No videos yet.</p>
              <p>Go to the home page and paste a YouTube URL to get started.</p>
            </>
          )}
        </div>
      ) : (
        <div className="video-grid">
          {videos.map((v) => (
            <VideoCard key={v.id || v.video_id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
