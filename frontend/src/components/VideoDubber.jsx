import React, { useState, useRef } from 'react';
import {
  Film,
  UploadCloud,
  FileVideo,
  Sparkles,
  Trash2,
  Download,
  Loader2,
  Clock,
  Gauge,
  CheckCircle2,
  VolumeX,
  Plus,
  ArrowUp,
  ArrowDown,
  Layers,
} from 'lucide-react';
import { dubVideo, fetchVideoHistory, deleteVideoHistoryItem } from '../services/api';

const VIDEO_SAMPLE_SCRIPTS = [
  'Đoạn video này ghi lại khoảnh khắc thiên nhiên tuyệt đẹp trong một buổi chiều hoàng hôn rực rỡ.',
  'Chào mừng các bạn đã đến với video hôm nay. Hãy cùng tôi khám phá những điều thú vị ngay sau đây!',
  'Công nghệ trí tuệ nhân tạo đang thay đổi cách chúng ta sáng tạo nội dung video mỗi ngày.',
];

export default function VideoDubber({ showToast }) {
  const [videoFiles, setVideoFiles] = useState([]);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState(0);
  const [text, setText] = useState('Đoạn video này ghi lại khoảnh khắc thiên nhiên tuyệt đẹp trong một buổi chiều hoàng hôn rực rỡ.');
  const [speed, setSpeed] = useState(1.0);
  const [removeOriginalAudio, setRemoveOriginalAudio] = useState(true);
  const [durationMode, setDurationMode] = useState('full_video'); // 'full_video' | 'match_voice' | 'loop_voice'
  const [isLoading, setIsLoading] = useState(false);
  const [dubbedResult, setDubbedResult] = useState(null);
  const [videoHistory, setVideoHistory] = useState([]);

  const fileInputRef = useRef(null);
  const addMoreInputRef = useRef(null);

  // Load video history on mount
  React.useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const items = await fetchVideoHistory();
      setVideoHistory(items);
    } catch (e) {
      console.error('Failed to load video history:', e);
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      const validVideos = files.filter((f) => f.type.startsWith('video/'));
      if (validVideos.length === 0) {
        showToast('Vui lòng chọn các file video hợp lệ (.mp4, .mov, .mkv, .webm)', 'error');
        return;
      }
      setVideoFiles((prev) => [...prev, ...validVideos]);
      setDubbedResult(null);
    }
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

  const handleProcessDubbing = async () => {
    if (videoFiles.length === 0) {
      showToast('Vui lòng tải lên ít nhất 1 video!', 'error');
      return;
    }
    if (!text.trim()) {
      showToast('Vui lòng nhập văn bản lời bình tiếng Việt!', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const result = await dubVideo(videoFiles, text, speed, removeOriginalAudio, durationMode);
      setDubbedResult(result);
      showToast(`Đã nối & lồng tiếng thành công ${videoFiles.length} video!`, 'success');
      loadHistory();
    } catch (error) {
      console.error('Dubbing error:', error);
      showToast(error.message || 'Lỗi khi xử lý lồng tiếng video', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteVideo = async (id) => {
    try {
      await deleteVideoHistoryItem(id);
      showToast('Đã xóa video trong lịch sử', 'success');
      if (dubbedResult?.id === id) {
        setDubbedResult(null);
      }
      loadHistory();
    } catch (e) {
      showToast('Lỗi khi xóa video: ' + e.message, 'error');
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
      {/* Left Column: Multi-Video Upload & Script */}
      <section className="column-left">
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Film size={20} className="card-header-icon" />
              <h2 className="card-title">
                {videoFiles.length > 1
                  ? `Nối & Lồng Tiếng (${videoFiles.length} Video)`
                  : 'Tải Lên Video & Lời Bình'}
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

          {/* Upload Dropzone (Supports Multiple Selection) */}
          {videoFiles.length === 0 ? (
            <div
              className="dropzone-box"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="video/*"
                multiple
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                <div className="dropzone-icon-pulse">
                  <UploadCloud size={32} className="dropzone-icon" />
                </div>
                <h4>Kéo thả hoặc Nhấp để chọn Nhiều Video</h4>
                <p>Hỗ trợ chọn cùng lúc 1 hoặc nhiều video MP4, MOV, MKV, WebM</p>
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

              {/* Video Playlist / Ordering List */}
              <div className="playlist-container">
                <div className="playlist-header">
                  <div className="playlist-title">
                    <Layers size={16} />
                    <span>Danh sách clip sẽ ghép nối theo thứ tự ({videoFiles.length} clips • {formatFileSize(totalFilesSize)}):</span>
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
                    onChange={handleFileChange}
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

          {/* Script Samples */}
          <div className="samples-container" style={{ marginTop: '16px' }}>
            <span className="samples-label">Lời bình mẫu:</span>
            <div className="samples-list">
              {VIDEO_SAMPLE_SCRIPTS.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="sample-chip"
                  onClick={() => setText(sample)}
                >
                  Mẫu {idx + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Text Area */}
          <div className="textarea-wrapper">
            <textarea
              className="tts-textarea"
              placeholder="Nhập văn bản lời bình / thuyết minh tiếng Việt xuyên suốt các video..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              disabled={isLoading}
            />
            <div className="textarea-footer">
              <span className="count-badge">{text.length} ký tự</span>
            </div>
          </div>

          {/* Speed & Audio Options */}
          <div className="controls-panel">
            <div className="speed-control-group">
              <div className="speed-header">
                <div className="speed-title">
                  <Gauge size={18} />
                  <span>Tốc độ giọng đọc:</span>
                </div>
                <span className="speed-value">{speed.toFixed(1)}x</span>
              </div>

              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                className="speed-slider"
                disabled={isLoading}
              />
            </div>

            {/* Duration Mode Options */}
            <div className="duration-mode-box">
              <span className="duration-mode-title">Chế độ độ dài video:</span>
              <div className="duration-options-list">
                <label className={`duration-option-pill ${durationMode === 'full_video' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="duration_mode"
                    value="full_video"
                    checked={durationMode === 'full_video'}
                    onChange={() => setDurationMode('full_video')}
                  />
                  <span>🎬 Giữ trọn vẹn toàn bộ độ dài Video (Nối hết tất cả clip)</span>
                </label>

                <label className={`duration-option-pill ${durationMode === 'match_voice' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="duration_mode"
                    value="match_voice"
                    checked={durationMode === 'match_voice'}
                    onChange={() => setDurationMode('match_voice')}
                  />
                  <span>✂️ Cắt ngắn video theo độ dài giọng đọc</span>
                </label>

                <label className={`duration-option-pill ${durationMode === 'loop_voice' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="duration_mode"
                    value="loop_voice"
                    checked={durationMode === 'loop_voice'}
                    onChange={() => setDurationMode('loop_voice')}
                  />
                  <span>🔁 Lặp lại giọng đọc đến hết video</span>
                </label>
              </div>
            </div>

            <label className="checkbox-control">
              <input
                type="checkbox"
                checked={removeOriginalAudio}
                onChange={(e) => setRemoveOriginalAudio(e.target.checked)}
              />
              <div className="checkbox-label-group">
                <VolumeX size={16} />
                <span>Xóa âm thanh gốc của tất cả video và thay bằng giọng đọc Ngọc Huyền</span>
              </div>
            </label>

            <button
              type="button"
              className={`btn-synthesize ${isLoading ? 'loading' : ''}`}
              onClick={handleProcessDubbing}
              disabled={isLoading || videoFiles.length === 0 || !text.trim()}
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="spin-icon" />
                  <span>
                    {videoFiles.length > 1
                      ? `Đang nối ${videoFiles.length} video & lồng tiếng...`
                      : 'Đang tạo giọng & ghép vào video...'}
                  </span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>
                    {videoFiles.length > 1
                      ? `Nối ${videoFiles.length} Video & Lồng Tiếng (.MP4)`
                      : 'Ghép Giọng Đọc Vào Video (.MP4)'}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Right Column: Result Video & History */}
      <section className="column-right">
        {dubbedResult ? (
          <div className="card player-card animate-fade-in">
            <div className="card-header">
              <div className="card-title-group">
                <CheckCircle2 size={20} className="card-header-icon" style={{ color: '#10b981' }} />
                <h2 className="card-title">Video Đã Ghép Hoàn Tất</h2>
              </div>

              <a
                href={dubbedResult.fullDownloadUrl}
                download={`dubbed_ngoc_huyen_${dubbedResult.id}.mp4`}
                className="btn-download"
              >
                <Download size={18} />
                <span>Tải Video MP4 ({formatFileSize(dubbedResult.file_size)})</span>
              </a>
            </div>

            {/* Video Player */}
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
              <span className="meta-pill">
                Tốc độ đọc: {dubbedResult.speed}x
              </span>
              {dubbedResult.video_count && (
                <span className="meta-pill">
                  Số clip đã nối: {dubbedResult.video_count}
                </span>
              )}
              <span className="meta-pill">
                Định dạng: MP4 (H.264 + AAC 192k)
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
              <p>Tải lên 1 hoặc nhiều video, nhập lời bình và bấm tạo để xem và tải về</p>
            </div>
          </div>
        )}

        {/* Video Dubbing History */}
        <div className="card history-card">
          <div className="card-header">
            <div className="card-title-group">
              <Film size={20} className="card-header-icon" />
              <h2 className="card-title">Video Đã Ghép Gần Đây ({videoHistory.length})</h2>
            </div>
          </div>

          {videoHistory.length === 0 ? (
            <div className="empty-sub" style={{ textAlign: 'center', padding: '16px' }}>
              Chưa có video lồng tiếng nào được lưu
            </div>
          ) : (
            <div className="history-items-list">
              {videoHistory.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-item-left" onClick={() => setDubbedResult(item)}>
                    <div className="history-text" title={item.text}>
                      "{item.text}"
                    </div>
                    <div className="history-metadata">
                      <span className="history-meta-tag">
                        <Clock size={12} /> {item.duration}s
                      </span>
                      <span className="history-meta-tag">
                        {formatFileSize(item.file_size)}
                      </span>
                    </div>
                  </div>

                  <div className="history-item-actions">
                    <a
                      href={item.fullDownloadUrl}
                      download={`dubbed_ngoc_huyen_${item.id}.mp4`}
                      className="btn-history-action download"
                      title="Tải video này"
                    >
                      <Download size={16} />
                    </a>

                    <button
                      type="button"
                      className="btn-history-action delete"
                      onClick={() => handleDeleteVideo(item.id)}
                      title="Xóa video"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
