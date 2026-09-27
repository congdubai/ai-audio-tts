import React, { useState, useEffect, useRef } from 'react';
import {
  Film,
  UploadCloud,
  FileVideo,
  Sparkles,
  Trash2,
  Download,
  Loader2,
  Clock,
  CheckCircle2,
  VolumeX,
  Volume2,
  Plus,
  ArrowUp,
  ArrowDown,
  Layers,
  Music,
  FileAudio,
  ListMusic,
  Disc,
  Gauge
} from 'lucide-react';
import { dubVideo, fetchHistory } from '../services/api';

export default function VideoDubber({ showToast, currentAudio }) {
  // Video States
  const [videoFiles, setVideoFiles] = useState([]);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState(0);

  // Voice Audio States
  const [audioSourceType, setAudioSourceType] = useState('history'); // 'history' | 'upload' | 'none'
  const [customAudioFile, setCustomAudioFile] = useState(null);
  const [customAudioUrl, setCustomAudioUrl] = useState(null);
  const [selectedAudioId, setSelectedAudioId] = useState('');
  const [historyAudios, setHistoryAudios] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Background Music (BGM) States
  const [bgmFile, setBgmFile] = useState(null);
  const [bgmUrl, setBgmUrl] = useState(null);
  const [bgmVolume, setBgmVolume] = useState(0.2); // Default 20% volume

  // Processing Options
  const [removeOriginalAudio, setRemoveOriginalAudio] = useState(true);
  const [durationMode, setDurationMode] = useState('full_video'); // 'full_video' | 'match_voice' | 'loop_voice'

  // App Execution States
  const [isLoading, setIsLoading] = useState(false);
  const [dubbedResult, setDubbedResult] = useState(null);

  // Refs
  const fileInputRef = useRef(null);
  const addMoreInputRef = useRef(null);
  const audioFileInputRef = useRef(null);
  const bgmFileInputRef = useRef(null);

  // Fetch TTS History on Mount
  useEffect(() => {
    loadAudioHistory();
  }, []);

  // Update selected audio ID if currentAudio changes
  useEffect(() => {
    if (currentAudio?.id) {
      setSelectedAudioId(currentAudio.id);
      setAudioSourceType('history');
    }
  }, [currentAudio]);

  const loadAudioHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const items = await fetchHistory();
      setHistoryAudios(items);

      if (currentAudio?.id) {
        setSelectedAudioId(currentAudio.id);
      } else if (items.length > 0 && !selectedAudioId) {
        setSelectedAudioId(items[0].id);
      }
    } catch (error) {
      console.warn('Unable to load audio history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Video File Handlers
  const isVideoFile = (f) => {
    if (f.type && f.type.startsWith('video/')) return true;
    return /\.(mp4|mov|mkv|webm|avi|flv|wmv|m4v|3gp)$/i.test(f.name);
  };

  const addValidVideos = (files) => {
    const validVideos = Array.from(files).filter(isVideoFile);
    if (validVideos.length === 0) {
      showToast('Vui lòng chọn các file video (.mp4, .mov, .mkv, .webm, .avi)', 'error');
      return;
    }
    setVideoFiles((prev) => [...prev, ...validVideos]);
    setDubbedResult(null);
  };

  const handleVideoFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      addValidVideos(files);
    }
  };

  const handleVideoDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addValidVideos(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleRemoveSingleVideo = (indexToRemove) => {
    setVideoFiles((prev) => {
      const updated = prev.filter((_, idx) => idx !== indexToRemove);
      if (selectedPreviewIndex >= updated.length) {
        setSelectedPreviewIndex(Math.max(0, updated.length - 1));
      }
      return updated;
    });
  };

  const handleClearAllVideos = () => {
    setVideoFiles([]);
    setSelectedPreviewIndex(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (addMoreInputRef.current) addMoreInputRef.current.value = '';
  };

  const moveVideoOrder = (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= videoFiles.length) return;

    setVideoFiles((prev) => {
      const copy = [...prev];
      const temp = copy[index];
      copy[index] = copy[targetIndex];
      copy[targetIndex] = temp;
      return copy;
    });
    setSelectedPreviewIndex(targetIndex);
  };

  // Custom Voice Audio Upload Handler
  const handleCustomAudioChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('audio/') && !/\.(wav|mp3|m4a|aac|flac|ogg)$/i.test(file.name)) {
        showToast('Vui lòng chọn file âm thanh (.wav, .mp3, .m4a, .aac, .flac, .ogg)', 'error');
        return;
      }
      setCustomAudioFile(file);
      setCustomAudioUrl(URL.createObjectURL(file));
      setAudioSourceType('upload');
    }
  };

  const clearCustomAudio = () => {
    setCustomAudioFile(null);
    setCustomAudioUrl(null);
    if (audioFileInputRef.current) audioFileInputRef.current.value = '';
  };

  // Background Music (BGM) Upload Handler
  const handleBgmChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('audio/') && !/\.(wav|mp3|m4a|aac|flac|ogg)$/i.test(file.name)) {
        showToast('Vui lòng chọn file nhạc nền (.mp3, .wav, .m4a, .aac, .flac, .ogg)', 'error');
        return;
      }
      setBgmFile(file);
      setBgmUrl(URL.createObjectURL(file));
      showToast('Đã tải lên file Nhạc Nền thành công!', 'success');
    }
  };

  const clearBgmFile = () => {
    setBgmFile(null);
    setBgmUrl(null);
    if (bgmFileInputRef.current) bgmFileInputRef.current.value = '';
  };

  // Main Processing Submit
  const handleProcessVideo = async () => {
    if (videoFiles.length === 0) {
      showToast('Vui lòng tải lên ít nhất 1 video!', 'error');
      return;
    }

    let audioFileToSend = null;
    let audioIdToSend = null;

    if (audioSourceType === 'upload') {
      if (!customAudioFile) {
        showToast('Vui lòng chọn file Audio Giọng Đọc!', 'error');
        return;
      }
      audioFileToSend = customAudioFile;
    } else if (audioSourceType === 'history') {
      if (!selectedAudioId) {
        showToast('Vui lòng chọn 1 bản ghi giọng đọc TTS từ danh sách!', 'error');
        return;
      }
      audioIdToSend = selectedAudioId;
    }

    setIsLoading(true);
    try {
      const result = await dubVideo(
        videoFiles,
        audioFileToSend,
        audioIdToSend,
        bgmFile,
        bgmVolume,
        removeOriginalAudio,
        durationMode
      );
      setDubbedResult(result);

      if (audioSourceType !== 'none' && bgmFile) {
        showToast(`Đã ghép thành công Video + Giọng Đọc + Nhạc Nền!`, 'success');
      } else if (audioSourceType !== 'none') {
        showToast(`Đã ghép Video + Giọng Đọc thành công!`, 'success');
      } else if (bgmFile) {
        showToast(`Đã ghép Video + Nhạc Nền thành công!`, 'success');
      } else if (removeOriginalAudio) {
        showToast(`Đã xóa âm thanh gốc của ${videoFiles.length} video!`, 'success');
      } else {
        showToast(`Đã nối ${videoFiles.length} video thành công!`, 'success');
      }
    } catch (error) {
      console.error('Video process error:', error);
      showToast(error.message || 'Lỗi khi xử lý video', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const totalFilesSize = videoFiles.reduce((acc, f) => acc + f.size, 0);
  const currentPreviewFile = videoFiles[selectedPreviewIndex];
  const currentPreviewUrl = currentPreviewFile ? URL.createObjectURL(currentPreviewFile) : null;

  return (
    <div className="content-grid">
      {/* Left Column: Input Options */}
      <section className="column-left">
        {/* Section 1: Video Files */}
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Film size={20} className="card-header-icon" />
              <h2 className="card-title">
                {videoFiles.length > 1
                  ? `1. Danh Sách Video Nối (${videoFiles.length} Clips)`
                  : '1. File Video Đầu Vào'}
              </h2>
            </div>
            {videoFiles.length > 0 && (
              <button
                type="button"
                className="btn-text-action"
                onClick={handleClearAllVideos}
                title="Xóa tất cả video"
              >
                <Trash2 size={16} /> Xóa tất cả
              </button>
            )}
          </div>

          {/* Upload Dropzone */}
          {videoFiles.length === 0 ? (
            <div
              className="dropzone-box"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDrop={handleVideoDrop}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleVideoFileChange}
                accept="video/*,.mp4,.mov,.mkv,.webm,.avi"
                multiple
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                <div className="dropzone-icon-pulse">
                  <UploadCloud size={32} className="dropzone-icon" />
                </div>
                <h4>Kéo thả hoặc Nhấp để chọn Video</h4>
                <p>Hỗ trợ chọn cùng lúc 1 hoặc nhiều clip MP4, MOV, MKV, WebM</p>
              </div>
            </div>
          ) : (
            <div className="multi-video-wrapper">
              {/* Active Video Preview */}
              {currentPreviewUrl && (
                <div className="video-preview-wrapper">
                  <video
                    key={currentPreviewUrl}
                    src={currentPreviewUrl}
                    controls
                    className="preview-video-element"
                  />
                  <div className="video-file-info">
                    <FileVideo size={16} />
                    <span>
                      Đang xem: <strong>Clip {selectedPreviewIndex + 1}/{videoFiles.length}</strong> - {currentPreviewFile.name} ({formatFileSize(currentPreviewFile.size)})
                    </span>
                  </div>
                </div>
              )}

              {/* Video Playlist */}
              <div className="playlist-container">
                <div className="playlist-header">
                  <div className="playlist-title">
                    <Layers size={16} />
                    <span>Danh sách clip ({videoFiles.length} clips • {formatFileSize(totalFilesSize)}):</span>
                  </div>

                  <button
                    type="button"
                    className="btn-add-more-video"
                    onClick={() => addMoreInputRef.current?.click()}
                  >
                    <Plus size={15} /> Thêm clip
                  </button>
                  <input
                    type="file"
                    ref={addMoreInputRef}
                    onChange={handleVideoFileChange}
                    accept="video/*"
                    multiple
                    style={{ display: 'none' }}
                  />
                </div>

                <div className="playlist-items-list">
                  {videoFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className={`playlist-item ${selectedPreviewIndex === idx ? 'active' : ''}`}
                    >
                      <div
                        className="playlist-item-left"
                        onClick={() => setSelectedPreviewIndex(idx)}
                      >
                        <span className="clip-number">#{idx + 1}</span>
                        <div className="clip-info">
                          <span className="clip-name">{file.name}</span>
                          <span className="clip-size">{formatFileSize(file.size)}</span>
                        </div>
                      </div>

                      <div className="playlist-item-actions">
                        <button
                          type="button"
                          className="btn-order-action"
                          onClick={() => moveVideoOrder(idx, -1)}
                          disabled={idx === 0}
                          title="Di chuyển lên trước"
                        >
                          <ArrowUp size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn-order-action"
                          onClick={() => moveVideoOrder(idx, 1)}
                          disabled={idx === videoFiles.length - 1}
                          title="Di chuyển xuống sau"
                        >
                          <ArrowDown size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn-order-action delete"
                          onClick={() => handleRemoveSingleVideo(idx)}
                          title="Xóa clip này"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 2: Voice Audio (Giọng Đọc Truyện) */}
        <div className="card" style={{ marginTop: '20px' }}>
          <div className="card-header">
            <div className="card-title-group">
              <Volume2 size={20} className="card-header-icon" style={{ color: '#6366f1' }} />
              <h2 className="card-title">2. Chọn Audio Giọng Đọc (Lời Bình / Thuyết Minh)</h2>
            </div>
          </div>

          {/* Voice Tabs */}
          <div className="audio-source-tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button
              type="button"
              className={`nav-tab-btn ${audioSourceType === 'history' ? 'active' : ''}`}
              onClick={() => setAudioSourceType('history')}
              style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
            >
              <ListMusic size={16} />
              <span>Chọn từ Lịch Sử TTS</span>
            </button>

            <button
              type="button"
              className={`nav-tab-btn ${audioSourceType === 'upload' ? 'active' : ''}`}
              onClick={() => setAudioSourceType('upload')}
              style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
            >
              <FileAudio size={16} />
              <span>Tải File Giọng Đọc</span>
            </button>

            <button
              type="button"
              className={`nav-tab-btn ${audioSourceType === 'none' ? 'active' : ''}`}
              onClick={() => setAudioSourceType('none')}
              style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
            >
              <VolumeX size={16} />
              <span>Không Dùng Giọng Đọc</span>
            </button>
          </div>

          {/* Content: History */}
          {audioSourceType === 'history' && (
            <div className="audio-history-picker" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {currentAudio && (
                <div
                  className={`audio-pick-card ${selectedAudioId === currentAudio.id ? 'selected' : ''}`}
                  onClick={() => setSelectedAudioId(currentAudio.id)}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '12px',
                    border: selectedAudioId === currentAudio.id ? '2px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                    background: selectedAudioId === currentAudio.id ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.03)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ padding: '8px', background: '#6366f1', borderRadius: '8px', color: 'white' }}>
                      <Volume2 size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#f8fafc' }}>
                        ⭐ Giọng đọc vừa tạo ở Tab TTS ({currentAudio.duration}s)
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        "{currentAudio.text}"
                      </div>
                    </div>
                  </div>
                  {selectedAudioId === currentAudio.id && (
                    <CheckCircle2 size={20} style={{ color: '#6366f1', flexShrink: 0 }} />
                  )}
                </div>
              )}

              <div className="select-wrapper">
                <label style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px', display: 'block' }}>
                  Danh sách giọng đọc TTS sẵn có:
                </label>
                <select
                  value={selectedAudioId}
                  onChange={(e) => setSelectedAudioId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    background: 'rgba(18, 22, 34, 0.95)',
                    color: '#f8fafc',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.9rem',
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  {historyAudios.length === 0 && !currentAudio && (
                    <option value="">(Chưa có giọng đọc nào trong lịch sử - Vui lòng tạo thử bên Tab 1)</option>
                  )}
                  {historyAudios.map((item) => (
                    <option key={item.id} value={item.id}>
                      🎙️ {item.text ? (item.text.length > 50 ? item.text.slice(0, 50) + '...' : item.text) : item.filename} ({item.duration}s)
                    </option>
                  ))}
                </select>
              </div>

              {selectedAudioId && (
                <div style={{ marginTop: '4px', padding: '10px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <audio
                    key={selectedAudioId}
                    src={`http://127.0.0.1:8000/api/tts/audio/${selectedAudioId}`}
                    controls
                    style={{ width: '100%', height: '36px' }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Content: Custom Upload */}
          {audioSourceType === 'upload' && (
            <div className="audio-upload-box">
              {!customAudioFile ? (
                <div
                  className="dropzone-box"
                  onClick={() => audioFileInputRef.current?.click()}
                  style={{ padding: '20px 16px' }}
                >
                  <input
                    type="file"
                    ref={audioFileInputRef}
                    onChange={handleCustomAudioChange}
                    accept="audio/*,.wav,.mp3,.m4a,.aac,.flac,.ogg"
                    style={{ display: 'none' }}
                  />
                  <div className="dropzone-content">
                    <FileAudio size={28} className="dropzone-icon" style={{ color: '#6366f1' }} />
                    <h4 style={{ marginTop: '8px', fontSize: '0.95rem' }}>Nhấp chọn file Giọng Đọc từ máy tính</h4>
                    <p style={{ fontSize: '0.8rem' }}>Hỗ trợ WAV, MP3, M4A, AAC, FLAC, OGG</p>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '14px 18px', background: 'rgba(99,102,241,0.12)', borderRadius: '12px', border: '1px solid rgba(99,102,241,0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <FileAudio size={20} style={{ color: '#6366f1' }} />
                      <div>
                        <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.92rem' }}>{customAudioFile.name}</div>
                        <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{formatFileSize(customAudioFile.size)}</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn-order-action delete"
                      onClick={clearCustomAudio}
                      title="Xóa file này"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {customAudioUrl && (
                    <audio src={customAudioUrl} controls style={{ width: '100%', height: '36px' }} />
                  )}
                </div>
              )}
            </div>
          )}

          {/* Content: None */}
          {audioSourceType === 'none' && (
            <div style={{ padding: '14px 18px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: '0.88rem' }}>
              Không sử dụng âm thanh giọng đọc (chỉ xử lý video hoặc lồng nhạc nền).
            </div>
          )}
        </div>

        {/* Section 3: Background Music (Nhạc Nền Truyện) */}
        <div className="card" style={{ marginTop: '20px' }}>
          <div className="card-header">
            <div className="card-title-group">
              <Disc size={20} className="card-header-icon" style={{ color: '#ec4899' }} />
              <h2 className="card-title">3. Tải Lên Nhạc Nền (Background Music)</h2>
            </div>
          </div>

          {!bgmFile ? (
            <div
              className="dropzone-box"
              onClick={() => bgmFileInputRef.current?.click()}
              style={{ padding: '22px 16px' }}
            >
              <input
                type="file"
                ref={bgmFileInputRef}
                onChange={handleBgmChange}
                accept="audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg"
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                <Music size={30} className="dropzone-icon" style={{ color: '#ec4899' }} />
                <h4 style={{ marginTop: '8px', fontSize: '0.95rem' }}>Nhấp để tải file Nhạc Nền từ máy tính</h4>
                <p style={{ fontSize: '0.8rem' }}>Chọn bài nhạc không lời hay hiệu ứng âm thanh (.MP3, .WAV, .M4A)</p>
              </div>
            </div>
          ) : (
            <div style={{ padding: '14px 18px', background: 'rgba(236,72,153,0.12)', borderRadius: '12px', border: '1px solid rgba(236,72,153,0.3)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Music size={20} style={{ color: '#ec4899' }} />
                  <div>
                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.92rem' }}>{bgmFile.name}</div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{formatFileSize(bgmFile.size)}</div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-order-action delete"
                  onClick={clearBgmFile}
                  title="Xóa nhạc nền"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              {bgmUrl && (
                <audio src={bgmUrl} controls style={{ width: '100%', height: '36px' }} />
              )}
            </div>
          )}

          {/* BGM Volume Slider (Active if BGM uploaded) */}
          {bgmFile && (
            <div className="speed-control-group" style={{ marginTop: '16px', background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '12px' }}>
              <div className="speed-header">
                <div className="speed-title">
                  <Gauge size={16} style={{ color: '#ec4899' }} />
                  <span>Âm lượng Nhạc nền (BGM):</span>
                </div>
                <span className="speed-value" style={{ color: '#ec4899' }}>
                  {Math.round(bgmVolume * 100)}%
                </span>
              </div>

              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                value={bgmVolume}
                onChange={(e) => setBgmVolume(parseFloat(e.target.value))}
                className="speed-slider"
                style={{ accentColor: '#ec4899' }}
              />
              <span style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '6px', display: 'block' }}>
                💡 Mức {Math.round(bgmVolume * 100)}% vừa đủ nghe êm dịu, không bị át giọng đọc truyện.
              </span>
            </div>
          )}
        </div>

        {/* Section 4: Output Options & Run */}
        <div className="card" style={{ marginTop: '20px' }}>
          <div className="card-header">
            <div className="card-title-group">
              <Sparkles size={20} className="card-header-icon" />
              <h2 className="card-title">4. Xử Lý & Xuất Video</h2>
            </div>
          </div>

          <div className="controls-panel">
            {/* Duration Mode options */}
            {(audioSourceType !== 'none' || bgmFile) && (
              <div className="duration-mode-box">
                <span className="duration-mode-title">Chế độ khớp độ dài video:</span>
                <div className="duration-options-list">
                  <label className={`duration-option-pill ${durationMode === 'full_video' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="duration_mode"
                      value="full_video"
                      checked={durationMode === 'full_video'}
                      onChange={() => setDurationMode('full_video')}
                    />
                    <span>🎬 Giữ trọn vẹn toàn bộ độ dài Video</span>
                  </label>

                  <label className={`duration-option-pill ${durationMode === 'match_voice' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="duration_mode"
                      value="match_voice"
                      checked={durationMode === 'match_voice'}
                      onChange={() => setDurationMode('match_voice')}
                    />
                    <span>✂️ Cắt ngắn video theo độ dài Giọng Đọc</span>
                  </label>

                  <label className={`duration-option-pill ${durationMode === 'loop_voice' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="duration_mode"
                      value="loop_voice"
                      checked={durationMode === 'loop_voice'}
                      onChange={() => setDurationMode('loop_voice')}
                    />
                    <span>🔁 Lặp lại Giọng Đọc đến hết video</span>
                  </label>
                </div>
              </div>
            )}

            {/* Checkbox: Mute Original Audio */}
            <label className="checkbox-control" style={{ marginTop: '12px' }}>
              <input
                type="checkbox"
                checked={removeOriginalAudio}
                onChange={(e) => setRemoveOriginalAudio(e.target.checked)}
              />
              <div className="checkbox-label-group">
                <VolumeX size={16} />
                <span>
                  Xóa âm thanh gốc của video gốc (Khuyên dùng khi lồng truyện & nhạc nền)
                </span>
              </div>
            </label>

            {/* Submit Action Button */}
            <button
              type="button"
              className={`btn-synthesize ${isLoading ? 'loading' : ''}`}
              onClick={handleProcessVideo}
              disabled={isLoading || videoFiles.length === 0}
              style={{ marginTop: '20px' }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="spin-icon" />
                  <span>Đang hòa âm & xử lý video bằng FFmpeg...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>
                    {audioSourceType !== 'none' && bgmFile
                      ? `✨ Ghép Video + Giọng Đọc + Nhạc Nền (.MP4)`
                      : audioSourceType !== 'none'
                      ? `✨ Ghép Video + Giọng Đọc (.MP4)`
                      : bgmFile
                      ? `✨ Ghép Video + Nhạc Nền (.MP4)`
                      : removeOriginalAudio
                      ? `✂️ Xóa Âm Thanh Gốc Video (.MP4)`
                      : `🎬 Nối Các Clip Video (.MP4)`}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Right Column: Result Video Player */}
      <section className="column-right">
        {dubbedResult ? (
          <div className="card player-card animate-fade-in">
            <div className="card-header">
              <div className="card-title-group">
                <CheckCircle2 size={20} className="card-header-icon" style={{ color: '#10b981' }} />
                <h2 className="card-title">Video Xử Lý Hoàn Tất</h2>
              </div>

              <a
                href={dubbedResult.fullDownloadUrl}
                download={`video_result_${dubbedResult.id}.mp4`}
                className="btn-download"
              >
                <Download size={18} />
                <span>Tải Video MP4 ({formatFileSize(dubbedResult.file_size)})</span>
              </a>
            </div>

            {/* Result Video Player */}
            <div className="dubbed-video-container">
              <video
                src={dubbedResult.fullVideoUrl}
                controls
                autoPlay
                className="dubbed-video-player"
              />
            </div>

            <div className="meta-tags-container">
              <span className="meta-pill">
                <Clock size={14} /> Thời lượng: {dubbedResult.duration}s
              </span>
              {dubbedResult.has_voice && (
                <span className="meta-pill">
                  🎙️ Đã ghép Giọng đọc
                </span>
              )}
              {dubbedResult.has_bgm && (
                <span className="meta-pill">
                  🎵 Nhạc nền ({Math.round((dubbedResult.bgm_volume || 0.2) * 100)}%)
                </span>
              )}
              {dubbedResult.video_count && (
                <span className="meta-pill">
                  Số clip đã nối: {dubbedResult.video_count}
                </span>
              )}
              <span className="meta-pill">
                Định dạng: MP4 (H.264 + AAC)
              </span>
            </div>
          </div>
        ) : (
          <div className="card player-card placeholder">
            <div className="placeholder-content">
              <div className="placeholder-pulse">
                <Film size={36} className="placeholder-icon" />
              </div>
              <h3>Xem trước Video kết quả</h3>
              <p>Tải lên video, chọn giọng đọc truyện & nhạc nền rồi bấm xử lý để xem và tải về</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
