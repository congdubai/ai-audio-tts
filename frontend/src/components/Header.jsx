import React from 'react';
import { Volume2, Sparkles, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Header({ serverStatus }) {
  const isOnline = serverStatus?.status === 'healthy';
  const device = serverStatus?.device ? serverStatus.device.toUpperCase() : 'CPU';

  return (
    <header className="header-container">
      <div className="header-content">
        <div className="logo-group">
          <div className="logo-icon-wrapper">
            <Volume2 className="logo-icon" size={28} />
          </div>
          <div>
            <div className="title-wrapper">
              <h1 className="app-title">Kokoro Vietnamese TTS</h1>
              <span className="badge-model">
                <Sparkles size={13} /> Giọng Ngọc Huyền
              </span>
            </div>
            <p className="app-subtitle">
              Chuyển đổi văn bản thành giọng đọc tự nhiên chuẩn tiếng Việt với AI chất lượng cao
            </p>
          </div>
        </div>

        <div className="status-group">
          <div className={`status-pill ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? (
              <>
                <CheckCircle2 size={16} className="status-icon" />
                <span>Backend Sẵn sàng</span>
              </>
            ) : (
              <>
                <AlertCircle size={16} className="status-icon" />
                <span>Đang kết nối...</span>
              </>
            )}
          </div>

          {isOnline && (
            <div className="device-pill">
              <Cpu size={15} />
              <span>Thiết bị: <strong>{device}</strong></span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
