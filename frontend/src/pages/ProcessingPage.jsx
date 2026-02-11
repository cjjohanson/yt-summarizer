import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getVideoStatus } from '../api';

const STEPS = [
  { key: 'downloading', label: 'Download audio' },
  { key: 'transcribing', label: 'Transcribe audio' },
  { key: 'summarizing', label: 'Generate summaries' },
  { key: 'completed', label: 'Done' },
];

const STATUS_ORDER = ['pending', 'downloading', 'transcribing', 'summarizing', 'completed'];

function getStepState(stepKey, currentStatus, lastActiveStatus) {
  const stepIdx = STATUS_ORDER.indexOf(stepKey);

  if (currentStatus === 'failed') {
    // lastActiveStatus tells us which step was running when it failed
    const failedIdx = STATUS_ORDER.indexOf(lastActiveStatus);
    if (failedIdx < 0) return 'failed';
    if (stepIdx < failedIdx) return 'completed';
    if (stepIdx === failedIdx) return 'failed';
    return 'pending';
  }

  const effectiveStatus = currentStatus === 'pending' ? 'downloading' : currentStatus;
  const currentIdx = STATUS_ORDER.indexOf(effectiveStatus);
  if (currentIdx < 0) return 'pending';
  if (stepIdx < currentIdx) return 'completed';
  if (stepIdx === currentIdx) return 'active';
  return 'pending';
}

const STEP_ICONS = {
  pending: '',
  active: '...',
  completed: '\u2713',
  failed: '\u2717',
};

export default function ProcessingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [lastActiveStatus, setLastActiveStatus] = useState('downloading');
  const [error, setError] = useState('');

  useEffect(() => {
    let interval;

    async function poll() {
      try {
        const data = await getVideoStatus(id);
        setStatus(data);

        // Track the last non-failed status so we know which step failed
        if (data.status !== 'failed' && data.status !== 'completed') {
          setLastActiveStatus(data.status);
        }

        if (data.status === 'completed') {
          clearInterval(interval);
          navigate(`/video/${id}`, { replace: true });
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setError(data.error_message || 'Processing failed.');
        }
      } catch {
        // keep polling
      }
    }

    poll();
    interval = setInterval(poll, 2000);

    return () => clearInterval(interval);
  }, [id]);

  const currentStatus = status?.status || 'pending';

  return (
    <div className="processing-container">
      <h2 className="processing-title">
        {status?.title || 'Processing video...'}
      </h2>

      <div className="stepper">
        {STEPS.map((step) => {
          const state = getStepState(step.key, currentStatus, lastActiveStatus);
          return (
            <div key={step.key} className={`step ${state}`}>
              <div className="step-icon">{STEP_ICONS[state]}</div>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      {status?.progress_detail && currentStatus !== 'failed' && (
        <div className="progress-detail">{status.progress_detail}</div>
      )}

      {currentStatus === 'failed' && (
        <div className="error-box">
          <p><strong>Processing failed</strong></p>
          <p>{error}</p>
          <button
            className="btn btn-primary btn-sm"
            style={{ marginTop: 12 }}
            onClick={() => navigate('/')}
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}
