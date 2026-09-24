import React from 'react';
import { History, Play, Download, Trash2, Clock, Calendar } from 'lucide-react';

export default function HistoryList({ history, onSelectAudio, onDeleteAudio }) {
  if (!history || history.length === 0) {
    return (
      <div className="card history-card empty">
        <History size={32} className="empty-icon" />
        <p className="empty-text">Chưa có lịch sử tạo giọng nói nào</p>
        <p className="empty-sub">Hãy nhập câu bất kỳ ở trên và nhấn Tạo Giọng Nói để bắt đầu</p>
      </div>
    );
  }

  const formatDate = (isoString) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString();
    } catch {
      return '';
    }
  };

  return (
    <div className="card history-card">
      <div className="card-header">
        <div className="card-title-group">
          <History size={20} className="card-header-icon" />
          <h2 className="card-title">Lịch Sử Tạo Gần Đây ({history.length})</h2>
        </div>
      </div>

      <div className="history-items-list">
        {history.map((item) => (
          <div key={item.id} className="history-item">
            <div className="history-item-left" onClick={() => onSelectAudio(item)}>
              <div className="history-text" title={item.text}>
                "{item.text}"
              </div>
              <div className="history-metadata">
                <span className="history-meta-tag">
                  <Clock size={12} /> {item.duration}s
                </span>
                <span className="history-meta-tag">
                  Tốc độ: {item.speed}x
                </span>
                <span className="history-meta-tag">
                  <Calendar size={12} /> {formatDate(item.created_at)}
                </span>
              </div>
            </div>

            <div className="history-item-actions">
              <button
                type="button"
                className="btn-history-action play"
                onClick={() => onSelectAudio(item)}
                title="Nghe đoạn này"
              >
                <Play size={16} />
              </button>

              <a
                href={item.fullDownloadUrl}
                download={`ngoc_huyen_${item.id}.wav`}
                className="btn-history-action download"
                title="Tải về file WAV"
              >
                <Download size={16} />
              </a>

              <button
                type="button"
                className="btn-history-action delete"
                onClick={() => onDeleteAudio(item.id)}
                title="Xóa bản ghi này"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
