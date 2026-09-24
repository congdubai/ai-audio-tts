import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TextEditor from './components/TextEditor';
import AudioPlayer from './components/AudioPlayer';
import HistoryList from './components/HistoryList';
import { checkHealth, synthesizeText, fetchHistory, deleteHistoryItem } from './services/api';
import { AlertCircle, CheckCircle, Sparkles } from 'lucide-react';

export default function App() {
  const [text, setText] = useState('Xin chào, tôi là giọng đọc Ngọc Huyền. Chúc bạn một ngày tốt lành và tràn đầy năng lượng!');
  const [speed, setSpeed] = useState(1.0);
  const [isLoading, setIsLoading] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [history, setHistory] = useState([]);
  const [notification, setNotification] = useState(null);

  // Poll server health & initial history
  useEffect(() => {
    loadHealth();
    loadHistory();

    const interval = setInterval(loadHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const showToast = (msg, type = 'info') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadHealth = async () => {
    const status = await checkHealth();
    setServerStatus(status);
  };

  const loadHistory = async () => {
    try {
      const items = await fetchHistory();
      setHistory(items);
      if (items.length > 0 && !currentAudio) {
        setCurrentAudio(items[0]);
      }
    } catch (e) {
      console.error('History load error:', e);
    }
  };

  const handleSynthesize = async () => {
    if (!text.trim()) {
      showToast('Vui lòng nhập văn bản tiếng Việt!', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const result = await synthesizeText(text, speed);
      setCurrentAudio(result);
      showToast('Tạo giọng nói thành công!', 'success');
      loadHistory();
    } catch (error) {
      console.error('Synthesis error:', error);
      showToast(error.message || 'Lỗi khi tạo giọng nói', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteHistory = async (id) => {
    try {
      await deleteHistoryItem(id);
      showToast('Đã xóa bản ghi thành công', 'success');
      if (currentAudio?.id === id) {
        setCurrentAudio(null);
      }
      loadHistory();
    } catch (e) {
      showToast('Lỗi khi xóa: ' + e.message, 'error');
    }
  };

  return (
    <div className="app-container">
      {/* Dynamic Background Glows */}
      <div className="bg-glow top-left" />
      <div className="bg-glow bottom-right" />

      {/* Toast Notification */}
      {notification && (
        <div className={`toast-notification ${notification.type}`}>
          {notification.type === 'error' ? (
            <AlertCircle size={18} />
          ) : (
            <CheckCircle size={18} />
          )}
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Main Container */}
      <div className="main-layout">
        <Header serverStatus={serverStatus} />

        <main className="content-grid">
          {/* Left Column: Input & Controls */}
          <section className="column-left">
            <TextEditor
              text={text}
              setText={setText}
              speed={speed}
              setSpeed={setSpeed}
              isLoading={isLoading}
              onSynthesize={handleSynthesize}
            />
          </section>

          {/* Right Column: Audio Player & History */}
          <section className="column-right">
            {currentAudio ? (
              <AudioPlayer audioData={currentAudio} />
            ) : (
              <div className="card player-card placeholder">
                <div className="placeholder-content">
                  <div className="placeholder-pulse">
                    <Sparkles size={36} className="placeholder-icon" />
                  </div>
                  <h3>Sẵn sàng tạo giọng đọc</h3>
                  <p>Nhập văn bản và bấm "Tạo Giọng Nói" để nghe thử & tải file WAV</p>
                </div>
              </div>
            )}

            <HistoryList
              history={history}
              onSelectAudio={(item) => setCurrentAudio(item)}
              onDeleteAudio={handleDeleteHistory}
            />
          </section>
        </main>

        <footer className="footer-bar">
          <p>
            Kokoro Vietnamese TTS Engine • Model Finetuned Giọng Ngọc Huyền • 24kHz High-Fidelity Audio
          </p>
        </footer>
      </div>
    </div>
  );
}
