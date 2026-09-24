import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Download,
  Clock,
  Zap,
  Music,
  Code2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export default function AudioPlayer({ audioData }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showPhonemes, setShowPhonemes] = useState(false);

  const audioRef = useRef(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      setCurrentTime(0);
      audioRef.current.load();
    }
  }, [audioData?.fullAudioUrl]);

  if (!audioData) return null;

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch((e) => {
        console.error('Play failed:', e);
      });
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || audioData.duration || 0);
    }
  };

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val;
      setIsMuted(val === 0);
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    if (isMuted) {
      audioRef.current.volume = volume || 0.8;
      setIsMuted(false);
    } else {
      audioRef.current.volume = 0;
      setIsMuted(true);
    }
  };

  const handleReplay = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="card player-card animate-fade-in">
      <audio
        ref={audioRef}
        src={audioData.fullAudioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="card-header">
        <div className="card-title-group">
          <Music size={20} className="card-header-icon highlight" />
          <h2 className="card-title">Âm Thanh Đã Tạo</h2>
        </div>

        {/* Download Button Header */}
        <a
          href={audioData.fullDownloadUrl}
          download={`ngoc_huyen_${audioData.id}.wav`}
          className="btn-download"
          id="btn-download-audio"
        >
          <Download size={18} />
          <span>Tải file WAV ({formatFileSize(audioData.file_size)})</span>
        </a>
      </div>

      {/* Waveform / Equalizer Animation Visualizer */}
      <div className="visualizer-box">
        <div className={`equalizer-bars ${isPlaying ? 'playing' : ''}`}>
          {[...Array(28)].map((_, i) => (
            <div
              key={i}
              className="eq-bar"
              style={{
                animationDelay: `${(i % 7) * 0.15}s`,
                height: isPlaying ? undefined : '18%',
              }}
            />
          ))}
        </div>
      </div>

      {/* Main Controls */}
      <div className="player-controls">
        <div className="time-display">{formatTime(currentTime)}</div>

        <input
          type="range"
          min="0"
          max={duration || audioData.duration || 100}
          step="0.05"
          value={currentTime}
          onChange={handleSeek}
          className="timeline-slider"
        />

        <div className="time-display total">
          {formatTime(duration || audioData.duration)}
        </div>
      </div>

      {/* Buttons bar */}
      <div className="player-buttons-row">
        <div className="center-buttons">
          <button
            type="button"
            className="btn-round-secondary"
            onClick={handleReplay}
            title="Phát lại từ đầu"
          >
            <RotateCcw size={18} />
          </button>

          <button
            type="button"
            className="btn-round-primary"
            onClick={togglePlay}
            title={isPlaying ? 'Tạm dừng' : 'Phát'}
          >
            {isPlaying ? <Pause size={24} /> : <Play size={24} className="play-icon-offset" />}
          </button>
        </div>

        {/* Volume */}
        <div className="volume-control">
          <button type="button" className="btn-icon-mute" onClick={toggleMute}>
            {isMuted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="volume-slider"
          />
        </div>
      </div>

      {/* Meta info tags */}
      <div className="meta-tags-container">
        <span className="meta-pill">
          <Clock size={14} /> Thời lượng: {audioData.duration}s
        </span>
        <span className="meta-pill">
          <Zap size={14} /> Xử lý: {audioData.elapsed_time}s
        </span>
        <span className="meta-pill">
          Tốc độ: {audioData.speed}x
        </span>
        <span className="meta-pill">
          Chuẩn: 24kHz WAV
        </span>
      </div>

      {/* Phonemes Accordion */}
      {audioData.phonemes && (
        <div className="phonemes-accordion">
          <button
            type="button"
            className="phonemes-toggle-btn"
            onClick={() => setShowPhonemes(!showPhonemes)}
          >
            <div className="phonemes-toggle-title">
              <Code2 size={16} />
              <span>Xem ký hiệu ngữ âm (Phonemes)</span>
            </div>
            {showPhonemes ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showPhonemes && (
            <div className="phonemes-content">
              <pre>{audioData.phonemes}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
