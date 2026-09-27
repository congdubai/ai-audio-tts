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
  Sliders,
  Scissors
} from 'lucide-react';
import { dubVideo, fetchHistory } from '../services/api';

export default function VideoDubber({ showToast, currentAudio }) {
  // Video States
  const [videoFiles, setVideoFiles] = useState([]);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState(0);

  // Audio States
  const [audioSourceType, setAudioSourceType] = useState('history'); // 'history' | 'upload' | 'none'
  const [customAudioFile, setCustomAudioFile] = useState(null);
  const [customAudioUrl, setCustomAudioUrl] = useState(null);
  const [selectedAudioId, setSelectedAudioId] = useState('');
  const [historyAudios, setHistoryAudios] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

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

      // Auto-select first item or currentAudio if available
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

  // Custom Audio Upload Handler
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
        showToast('Vui lòng chọn file Audio để lồng tiếng!', 'error');
        return;
      }
      audioFileToSend = customAudioFile;
    } else if (audioSourceType === 'history') {
      if (!selectedAudioId) {
        showToast('Vui lòng chọn 1 bản ghi audio TTS từ danh sách!', 'error');
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
        removeOriginalAudio,
        durationMode
      );
      setDubbedResult(result);

      if (audioSourceType !== 'none') {
        showToast(`Đã lồng tiếng & ghép ${videoFiles.length} video thành công!`, 'success');
      } else if (removeOriginalAudio) {
        showToast(`Đã xóa âm thanh gốc của ${videoFiles.length} video thành công!`, 'success');
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

  // Selected history audio details
  const selectedHistoryAudioItem = historyAudios.find((a) => a.id === selectedAudioId) ||
    (currentAudio?.id === selectedAudioId ? currentAudio : null);

  return (
    <div className="content-grid">
      {/* Left Column: Video & Audio Options */}
      <section className="column-left">
        {/* Card 1: Video Upload & Playlist */}
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Film size={20} className="card-header-icon" />
              <h2 className="card-title">
                {videoFiles.length > 1
                  ? `Danh Sách Video Nối (${videoFiles.length} Clips)`
                  : '1. Chọn Video Đầu Vào'}
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
                    <span>Danh sách clip sẽ xử lý ({videoFiles.length} clips • {formatFileSize(totalFilesSize)}):</span>
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

        {/* Card 2: Audio Source & Processing Options */}
        <div className="card" style={{ marginTop: '20px' }}>
          <div className="card-header">
            <div className="card-title-group">
              <Music size={20} className="card-header-icon" style={{ color: '#8b5cf6' }} />
              <h2 className="card-title">2. Chọn Âm Thanh Lồng Tiếng</h2>
            </div>
          </div>

          {/* Audio Source Tabs */}
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
              <span>Tải File Audio (.WAV/.MP3)</span>
            </button>

            <button
              type="button"
              className={`nav-tab-btn ${audioSourceType === 'none' ? 'active' : ''}`}
              onClick={() => setAudioSourceType('none')}
              style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
            >
              <VolumeX size={16} />
              <span>Không Dùng Audio</span>
            </button>
          </div>

          {/* Tab Content 1: History TTS Selection */}
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
                    justify: 'space-between'
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

              {/* Dropdown Select for History */}
              <div className="select-wrapper">
                <label style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px', display: 'block' }}>
                  Danh sách file audio đã tạo trước đó:
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
                    <option value="">(Chưa có file audio nào trong lịch sử - Vui lòng chuyển sang tab 1 tạo thử hoặc tải file từ máy)</option>
                  )}
                  {historyAudios.map((item) => (
                    <option key={item.id} value={item.id}>
                      🎵 {item.text ? (item.text.length > 50 ? item.text.slice(0, 50) + '...' : item.text) : item.filename} ({item.duration}s)
                    </option>
                  ))}
                </select>
              </div>

              {/* Audio Preview Player */}
              {selectedAudioId && (
                <div style={{ marginTop: '8px', padding: '10px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
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

          {/* Tab Content 2: Custom Audio Upload */}
          {audioSourceType === 'upload' && (
            <div className="audio-upload-box">
              {!customAudioFile ? (
                <div
                  className="dropzone-box"
                  onClick={() => audioFileInputRef.current?.click()}
                  style={{ padding: '24px 16px' }}
                >
                  <input
                    type="file"
                    ref={audioFileInputRef}
                    onChange={handleCustomAudioChange}
                    accept="audio/*,.wav,.mp3,.m4a,.aac,.flac,.ogg"
                    style={{ display: 'none' }}
                  />
                  <div className="dropzone-content">
                    <FileAudio size={28} className="dropzone-icon" style={{ color: '#8b5cf6' }} />
                    <h4 style={{ marginTop: '8px', fontSize: '0.95rem' }}>Nhấp để chọn file Audio từ máy tính</h4>
                    <p style={{ fontSize: '0.8rem' }}>Hỗ trợ WAV, MP3, M4A, AAC, FLAC, OGG</p>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '14px 18px', background: 'rgba(139,92,246,0.12)', borderRadius: '12px', border: '1px solid rgba(139,92,246,0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <FileAudio size={20} style={{ color: '#8b5cf6' }} />
                      <div>
                        <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.92rem' }}>{customAudioFile.name}</div>
                        <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{formatFileSize(customAudioFile.size)}</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn-order-action delete"
                      onClick={clearCustomAudio}
                      title="Xóa file audio này"
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

          {/* Tab Content 3: No Audio */}
          {audioSourceType === 'none' && (
            <div style={{ padding: '16px 20px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <VolumeX size={24} style={{ color: '#ef4444', flexShrink: 0 }} />
              <div>
                <strong style={{ color: '#f8fafc', display: 'block' }}>Chế độ chỉ xử lý Video:</strong>
                Bạn có thể tick tùy chọn bên dưới để <strong>xóa âm thanh gốc</strong> của video hoặc <strong>chỉ nối các video</strong> lại với nhau mà không chèn nhạc.
              </div>
            </div>
          )}

          {/* Controls Panel (Options & Duration Mode) */}
          <div className="controls-panel" style={{ marginTop: '20px' }}>
            {/* Duration Mode options only if audio is provided */}
            {audioSourceType !== 'none' && (
              <div className="duration-mode-box">
                <span className="duration-mode-title">Chế độ khớp độ dài video & audio:</span>
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
                    <span>✂️ Cắt ngắn video theo độ dài Audio</span>
                  </label>

                  <label className={`duration-option-pill ${durationMode === 'loop_voice' ? 'active' : ''}`}>
                    <input
                      type="radio"
                      name="duration_mode"
                      value="loop_voice"
                      checked={durationMode === 'loop_voice'}
                      onChange={() => setDurationMode('loop_voice')}
                    />
                    <span>🔁 Lặp lại Audio đến hết video</span>
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
                  {audioSourceType !== 'none'
                    ? 'Xóa âm thanh gốc của video và thay bằng file Audio chọn ở trên'
                    : 'Xóa âm thanh gốc của tất cả các video (Xuất ra video im lặng)'}
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
                  <span>
                    {videoFiles.length > 1
                      ? `Đang nối ${videoFiles.length} video & xử lý FFmpeg...`
                      : 'Đang xử lý video bằng FFmpeg...'}
                  </span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>
                    {audioSourceType !== 'none'
                      ? (videoFiles.length > 1 ? `Nối ${videoFiles.length} Video & Ghép Audio (.MP4)` : 'Ghép Audio Vào Video (.MP4)')
                      : (removeOriginalAudio ? `Xóa Âm Gốc ${videoFiles.length > 1 ? videoFiles.length + ' Video' : 'Video'} (.MP4)` : `Nối ${videoFiles.length} Clip Video (.MP4)`)}
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
              {dubbedResult.video_count && (
                <span className="meta-pill">
                  Số clip đã nối: {dubbedResult.video_count}
                </span>
              )}
              <span className="meta-pill">
                Âm gốc: {dubbedResult.remove_original_audio ? 'Đã xóa' : 'Giữ nguyên'}
              </span>
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
              <p>Tải lên video, chọn file âm thanh (hoặc tùy chọn xóa âm) và bấm nút xử lý để xem và tải về</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
