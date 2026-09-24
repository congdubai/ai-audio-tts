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
} from 'lucide-react';
import { dubVideo, fetchVideoHistory, deleteVideoHistoryItem } from '../services/api';

const VIDEO_SAMPLE_SCRIPTS = [
  'Đoạn video này ghi lại khoảnh khắc thiên nhiên tuyệt đẹp trong một buổi chiều hoàng hôn rực rỡ.',
  'Chào mừng các bạn đã đến với video hôm nay. Hãy cùng tôi khám phá những điều thú vị ngay sau đây!',
  'Công nghệ trí tuệ nhân tạo đang thay đổi cách chúng ta sáng tạo nội dung video mỗi ngày.',
];

export default function VideoDubber({ showToast }) {
  const [videoFile, setVideoFile] = useState(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);
  const [text, setText] = useState('Đoạn video này ghi lại khoảnh khắc thiên nhiên tuyệt đẹp trong một buổi chiều hoàng hôn rực rỡ.');
  const [speed, setSpeed] = useState(1.0);
  const [removeOriginalAudio, setRemoveOriginalAudio] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [dubbedResult, setDubbedResult] = useState(null);
  const [videoHistory, setVideoHistory] = useState([]);

  const fileInputRef = useRef(null);

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
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        showToast('Vui lòng chọn một file video hợp lệ (.mp4, .mov, .mkv, .webm)', 'error');
        return;
      }
      setVideoFile(file);
      setVideoPreviewUrl(URL.createObjectURL(file));
      setDubbedResult(null);
    }
  };

  const handleRemoveFile = () => {
    setVideoFile(null);
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
      setVideoPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleProcessDubbing = async () => {
    if (!videoFile) {
      showToast('Vui lòng tải lên một video trước!', 'error');
      return;
    }
    if (!text.trim()) {
      showToast('Vui lòng nhập văn bản lời bình tiếng Việt!', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const result = await dubVideo(videoFile, text, speed, removeOriginalAudio);
      setDubbedResult(result);
      showToast('Lồng tiếng video thành công!', 'success');
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

  return (
    <div className="content-grid">
      {/* Left Column: Video Upload & Script */}
      <section className="column-left">
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Film size={20} className="card-header-icon" />
              <h2 className="card-title">Tải Lên Video & Lời Bình</h2>
            </div>
            {videoFile && (
              <button
                type="button"
                className="btn-text-action"
                onClick={handleRemoveFile}
                title="Đổi video khác"
              >
                <Trash2 size={16} /> Đổi video
              </button>
            )}
          </div>

          {/* Upload Dropzone */}
          {!videoFile ? (
            <div
              className="dropzone-box"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="video/*"
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                <div className="dropzone-icon-pulse">
                  <UploadCloud size={32} className="dropzone-icon" />
                </div>
                <h4>Kéo thả hoặc Nhấp để chọn Video</h4>
                <p>Hỗ trợ MP4, MOV, MKV, WebM</p>
              </div>
            </div>
          ) : (
            <div className="video-preview-wrapper">
              <video
                src={videoPreviewUrl}
                controls
                className="preview-video-element"
              />
              <div className="video-file-info">
                <FileVideo size={16} />
                <span>{videoFile.name} ({formatFileSize(videoFile.size)})</span>
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
              placeholder="Nhập văn bản lời bình / thuyết minh tiếng Việt để ghép vào video..."
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

            <label className="checkbox-control">
              <input
                type="checkbox"
                checked={removeOriginalAudio}
                onChange={(e) => setRemoveOriginalAudio(e.target.checked)}
              />
              <div className="checkbox-label-group">
                <VolumeX size={16} />
                <span>Xóa âm thanh gốc của video và thay thế bằng giọng đọc Ngọc Huyền</span>
              </div>
            </label>

            <button
              type="button"
              className={`btn-synthesize ${isLoading ? 'loading' : ''}`}
              onClick={handleProcessDubbing}
              disabled={isLoading || !videoFile || !text.trim()}
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="spin-icon" />
                  <span>Đang tạo giọng & ghép vào video...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>Ghép Giọng Đọc Vào Video (.MP4)</span>
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
                <h2 className="card-title">Video Đã Lồng Tiếng Hoàn Tất</h2>
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
                <Clock size={14} /> Thời lượng thoại: {dubbedResult.duration}s
              </span>
              <span className="meta-pill">
                Tốc độ đọc: {dubbedResult.speed}x
              </span>
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
              <p>Tải video lên, nhập lời bình và bấm "Ghép Giọng Đọc Vào Video" để xem và tải về</p>
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
