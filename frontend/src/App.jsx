import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage';
import VideoPage from './pages/VideoPage';
import LibraryPage from './pages/LibraryPage';
import ProcessingPage from './pages/ProcessingPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="header-inner">
            <Link to="/" className="logo">YT Summarizer</Link>
            <nav className="nav">
              <Link to="/">Home</Link>
              <Link to="/library">Library</Link>
            </nav>
          </div>
        </header>
        <main className="main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/video/:id" element={<VideoPage />} />
            <Route path="/video/:id/processing" element={<ProcessingPage />} />
            <Route path="/library" element={<LibraryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
