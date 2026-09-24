import React from 'react';
import { Sparkles, Trash2, Gauge, BookOpen, Loader2 } from 'lucide-react';

const SAMPLE_TEXTS = [
  {
    title: '👋 Giới thiệu',
    text: 'Xin chào quý vị và các bạn! Tôi là Ngọc Huyền, trợ lý giọng đọc trí tuệ nhân tạo tiếng Việt.',
  },
  {
    title: '📰 Bản tin thời sự',
    text: 'Dự báo thời tiết hôm nay, các tỉnh Bắc Bộ tiếp tục có nắng đẹp, nhiệt độ dao động từ hai mươi lăm đến ba mươi hai độ C.',
  },
  {
    title: '📖 Kể chuyện',
    text: 'Ngày xửa ngày xưa, ở một ngôi làng yên bình nằm bên dòng sông xanh biếc, có một người thợ mộc tài hoa và nhân hậu.',
  },
  {
    title: '🔬 Khoa học công nghệ',
    text: 'Trí tuệ nhân tạo đang tạo ra những bước tiến đột phá, giúp chuyển đổi văn bản thành âm thanh với ngữ điệu vô cùng chân thực.',
  },
];

export default function TextEditor({
  text,
  setText,
  speed,
  setSpeed,
  isLoading,
  onSynthesize,
}) {
  const charCount = text.length;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  const handleSampleClick = (sampleText) => {
    setText(sampleText);
  };

  const handleClear = () => {
    setText('');
  };

  return (
    <div className="card editor-card">
      <div className="card-header">
        <div className="card-title-group">
          <BookOpen size={20} className="card-header-icon" />
          <h2 className="card-title">Nhập Văn Bản Tiếng Việt</h2>
        </div>
        {text && (
          <button
            type="button"
            className="btn-text-action"
            onClick={handleClear}
            title="Xóa văn bản"
          >
            <Trash2 size={16} /> Xóa sạch
          </button>
        )}
      </div>

      {/* Preset samples */}
      <div className="samples-container">
        <span className="samples-label">Câu mẫu:</span>
        <div className="samples-list">
          {SAMPLE_TEXTS.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              className="sample-chip"
              onClick={() => handleSampleClick(sample.text)}
            >
              {sample.title}
            </button>
          ))}
        </div>
      </div>

      {/* Text Area */}
      <div className="textarea-wrapper">
        <textarea
          id="tts-input-textarea"
          className="tts-textarea"
          placeholder="Nhập hoặc dán văn bản tiếng Việt bạn muốn chuyển thành giọng nói tại đây..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          disabled={isLoading}
        />
        <div className="textarea-footer">
          <span className="count-badge">
            {charCount} ký tự • {wordCount} từ
          </span>
        </div>
      </div>

      {/* Speed & Actions Bar */}
      <div className="controls-panel">
        <div className="speed-control-group">
          <div className="speed-header">
            <div className="speed-title">
              <Gauge size={18} />
              <span>Tốc độ đọc:</span>
            </div>
            <span className="speed-value">{speed.toFixed(1)}x</span>
          </div>

          <div className="speed-slider-container">
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
            <div className="speed-ticks">
              {[0.8, 1.0, 1.2, 1.5].map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`speed-tick-btn ${speed === s ? 'active' : ''}`}
                  onClick={() => setSpeed(s)}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          type="button"
          id="btn-synthesize"
          className={`btn-synthesize ${isLoading ? 'loading' : ''}`}
          onClick={onSynthesize}
          disabled={isLoading || !text.trim()}
        >
          {isLoading ? (
            <>
              <Loader2 size={20} className="spin-icon" />
              <span>Đang tạo giọng nói...</span>
            </>
          ) : (
            <>
              <Sparkles size={20} />
              <span>Tạo Giọng Nói (Ngọc Huyền)</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
