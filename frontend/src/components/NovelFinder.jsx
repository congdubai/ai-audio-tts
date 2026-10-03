import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search, BookMarked, LogIn, Square, ExternalLink, ThumbsUp, Languages, X, Loader2,
  RefreshCw, Terminal, AlertTriangle, CheckCircle2, Info, Cpu, EyeOff, ShieldAlert,
  Plus, ChevronDown, ChevronUp, FileJson, FileSpreadsheet, ScrollText,
} from 'lucide-react';
import {
  fetchZhihuStatus, zhihuLoginStream, zhihuSearchStream, cancelZhihuJob, getZhihuExportUrl,
} from '../services/api';

const LOG_ICONS = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: ShieldAlert,
};

const formatVotes = (n) => {
  if (!n) return '0';
  if (n >= 10000) return `${(n / 10000).toFixed(1).replace(/\.0$/, '')} vạn`;
  return n.toLocaleString('vi-VN');
};

const nowTime = () => new Date().toLocaleTimeString('vi-VN', { hour12: false });

function ResultCard({ item, index, showOriginal }) {
  const [expanded, setExpanded] = useState(false);
  const title = (showOriginal && item.title_vi ? item.title_vi : item.title) || '(Không có tiêu đề)';
  const subTitle = item.title_vi && !showOriginal ? item.title_vi : null;
  const excerpt = (showOriginal && item.excerpt_vi ? item.excerpt_vi : item.excerpt) || '';

  return (
    <article className="nf-result-card" style={{ animationDelay: `${Math.min(index, 12) * 40}ms` }}>
      <div className="nf-result-rank">#{index + 1}</div>
      <div className="nf-result-body">
        {/* Trường 1: Tiêu đề + Lượt vote */}
        <div className="nf-result-top">
          <h3 className="nf-result-title">
            {item.link ? (
              <a href={item.link} target="_blank" rel="noreferrer" id={`nf-result-link-${index}`}>
                {title} <ExternalLink size={13} />
              </a>
            ) : title}
          </h3>
          <span className="nf-vote-pill" title={`${item.votes} lượt tán thành`}>
            <ThumbsUp size={13} /> {formatVotes(item.votes)}
          </span>
        </div>

        {subTitle && <p className="nf-result-subtitle">Dịch: {subTitle}</p>}

        <div className="nf-result-tags">
          {String(item.genre_vi || '').split(', ').filter(Boolean).map((g, i) => (
            <span key={g} className="nf-tag">
              {g} <em>({String(item.genre_cn || '').split(', ')[i]})</em>
            </span>
          ))}
        </div>

        {/* Trường 2: Nội dung / Đoạn trích */}
        {excerpt && (
          <>
            <p className={`nf-result-excerpt ${expanded ? 'expanded' : ''}`}>{excerpt}</p>
            {excerpt.length > 220 && (
              <button type="button" className="nf-expand-btn" onClick={() => setExpanded((v) => !v)}>
                {expanded ? <><ChevronUp size={14} /> Thu gọn</> : <><ChevronDown size={14} /> Xem thêm đầy đủ</>}
              </button>
            )}
          </>
        )}
      </div>
    </article>
  );
}

export default function NovelFinder({ showToast }) {
  const [status, setStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const [genres, setGenres] = useState(['tiên hiệp', 'trọng sinh']);
  const [genreInput, setGenreInput] = useState('');
  const [scrolls, setScrolls] = useState(4);
  const [translateEnabled, setTranslateEnabled] = useState(false);
  const [model, setModel] = useState('');
  const [headless, setHeadless] = useState(false);
  const [waitCaptcha, setWaitCaptcha] = useState(false);
  const [showAllSuggestions, setShowAllSuggestions] = useState(false);

  const [running, setRunning] = useState(null); // null | 'search' | 'login'
  const [progress, setProgress] = useState(null);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [filter, setFilter] = useState('');

  const jobIdRef = useRef(null);
  const abortRef = useRef(null);
  const logEndRef = useRef(null);

  const loadStatus = async () => {
    setStatusLoading(true);
    try {
      const s = await fetchZhihuStatus();
      setStatus(s);
      setModel((m) => m || (s.ollama_models.includes(s.default_model) ? s.default_model : s.ollama_models[0] || s.default_model));
    } catch (e) {
      setStatus({ error: e.message });
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    return () => abortRef.current?.abort();
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [logs]);

  const addLog = (message, level = 'info') => {
    setLogs((prev) => [...prev.slice(-199), { time: nowTime(), message, level }]);
  };

  const addGenre = (raw) => {
    const parts = String(raw).split(/[,;\n]/).map((s) => s.trim()).filter(Boolean);
    if (!parts.length) return;
    setGenres((prev) => {
      const next = [...prev];
      for (const p of parts) {
        if (!next.some((g) => g.toLowerCase() === p.toLowerCase()) && next.length < 20) next.push(p);
      }
      return next;
    });
    setGenreInput('');
  };

  const removeGenre = (g) => setGenres((prev) => prev.filter((x) => x !== g));

  const handlers = {
    onStart: (id) => { jobIdRef.current = id; },
    onProgress: (p) => setProgress(p),
    onLog: (l) => addLog(l.message, l.level),
  };

  const runJob = async (kind, fn) => {
    setRunning(kind);
    setError(null);
    setProgress({ percent: 0, message: 'Đang kết nối máy chủ...' });
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      return await fn(controller.signal);
    } catch (e) {
      if (e.name === 'AbortError') {
        addLog('Đã huỷ.', 'warning');
        return null;
      }
      addLog(e.message, e.code === 'cancelled' ? 'warning' : 'error');
      if (e.code !== 'cancelled') {
        setError(e);
        showToast?.(e.message, 'error');
      }
      return null;
    } finally {
      setRunning(null);
      setProgress(null);
      jobIdRef.current = null;
      abortRef.current = null;
    }
  };

  const handleLogin = async () => {
    addLog('Mở trình duyệt để đăng nhập Zhihu...');
    const res = await runJob('login', (signal) => zhihuLoginStream(handlers, signal));
    if (res?.logged_in) {
      showToast?.('Đăng nhập Zhihu thành công!', 'success');
      loadStatus();
    }
  };

  const handleSearch = async () => {
    const pending = genreInput.trim();
    const list = pending ? [...genres, pending] : genres;
    if (pending) addGenre(pending);
    if (!list.length) {
      showToast?.('Vui lòng nhập ít nhất một thể loại!', 'error');
      return;
    }
    setResult(null);
    addLog(`Bắt đầu tìm: ${list.join(', ')} (cuộn ${scrolls} lần, ${translateEnabled ? `dịch bằng ${model}` : 'không dịch'})`);
    const res = await runJob('search', (signal) => zhihuSearchStream({
      genres: list,
      scrolls,
      translate: translateEnabled,
      model: model || null,
      headless,
      wait_captcha: waitCaptcha,
    }, handlers, signal));
    if (res) {
      setResult(res);
      showToast?.(`Tìm thấy ${res.count} kết quả!`, 'success');
      loadStatus();
    }
  };

  const handleCancel = async () => {
    addLog('Đang gửi yêu cầu huỷ...', 'warning');
    await cancelZhihuJob(jobIdRef.current);
    // Nếu server không phản hồi kịp thì ngắt kết nối luôn (server sẽ tự dừng worker)
    setTimeout(() => abortRef.current?.abort(), 4000);
  };

  const filteredResults = useMemo(() => {
    const items = result?.results || [];
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) =>
      [it.title, it.title_vi, it.excerpt, it.excerpt_vi, it.genre_vi]
        .some((v) => String(v || '').toLowerCase().includes(q)));
  }, [result, filter]);

  const isBusy = Boolean(running);
  const ollamaOk = status?.ollama_running;
  const loggedIn = status?.zhihu_logged_in;
  const suggestions = (status?.genre_suggestions || []).filter(
    (s) => !genres.some((g) => g.toLowerCase() === s.toLowerCase()),
  );

  return (
    <div className="content-grid nf-grid">
      {/* ============ Cột trái: cấu hình ============ */}
      <section className="column-left">
        <div className="card nf-config-card">
          <div className="card-header">
            <div className="card-title-group">
              <BookMarked size={20} className="card-header-icon" />
              <h2 className="card-title">Tìm Truyện Zhihu</h2>
            </div>
            <button type="button" className="btn-text-action nf-refresh" onClick={loadStatus}
              disabled={statusLoading} title="Kiểm tra lại trạng thái" id="nf-refresh-status">
              <RefreshCw size={15} className={statusLoading ? 'spin-icon' : ''} /> Kiểm tra
            </button>
          </div>

          {/* Trạng thái */}
          <div className="nf-status-row">
            <span className={`status-pill ${ollamaOk ? 'online' : 'offline'}`}
              title={status?.ollama_error || ''}>
              <Cpu size={14} /> Ollama: {status ? (ollamaOk ? 'đang chạy' : 'chưa chạy') : '...'}
            </span>
            <span className={`status-pill ${loggedIn ? 'online' : 'offline'}`}>
              <LogIn size={14} /> Zhihu: {loggedIn ? 'đã đăng nhập' : 'chưa đăng nhập'}
            </span>
          </div>
          {status?.ollama_error && (
            <div className="nf-alert warning">
              <AlertTriangle size={16} />
              <span>{status.ollama_error}</span>
            </div>
          )}
          {status?.error && (
            <div className="nf-alert error">
              <ShieldAlert size={16} />
              <span>Không kết nối được backend: {status.error}</span>
            </div>
          )}

          {/* Thể loại */}
          <label className="nf-label" htmlFor="nf-genre-input">Thể loại / từ khoá (tiếng Việt)</label>
          <div className={`nf-chip-input ${isBusy ? 'disabled' : ''}`}>
            {genres.map((g) => (
              <span key={g} className="nf-chip">
                {g}
                {!isBusy && (
                  <button type="button" onClick={() => removeGenre(g)} aria-label={`Xoá ${g}`}>
                    <X size={12} />
                  </button>
                )}
              </span>
            ))}
            <input
              id="nf-genre-input"
              value={genreInput}
              disabled={isBusy}
              placeholder={genres.length ? 'Thêm thể loại...' : 'VD: tiên hiệp, nữ cường, gia đình hối hận'}
              onChange={(e) => setGenreInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ',') {
                  e.preventDefault();
                  addGenre(genreInput);
                } else if (e.key === 'Backspace' && !genreInput && genres.length) {
                  removeGenre(genres[genres.length - 1]);
                }
              }}
              onBlur={() => genreInput.trim() && addGenre(genreInput)}
            />
          </div>
          <p className="nf-hint">Enter hoặc dấu phẩy để thêm. Từ không có trong bảng sẽ được model dịch sang tiếng Trung.</p>

          {suggestions.length > 0 && (
            <div className="samples-container nf-suggestions">
              <div className="nf-suggestions-header">
                <span className="samples-label">Gợi ý thể loại ({suggestions.length}):</span>
                {suggestions.length > 16 && (
                  <button
                    type="button"
                    className="nf-toggle-suggestions-btn"
                    onClick={() => setShowAllSuggestions((prev) => !prev)}
                  >
                    {showAllSuggestions ? (
                      <><ChevronUp size={13} /> Thu gọn</>
                    ) : (
                      <><ChevronDown size={13} /> Xem tất cả ({suggestions.length})</>
                    )}
                  </button>
                )}
              </div>
              <div className={`samples-list nf-suggestions-list ${showAllSuggestions ? 'expanded' : ''}`}>
                {(showAllSuggestions ? suggestions : suggestions.slice(0, 16)).map((s) => (
                  <button key={s} type="button" className="sample-chip" disabled={isBusy} onClick={() => addGenre(s)}>
                    <Plus size={11} /> {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tuỳ chọn */}
          <div className="nf-options">
            <div className="speed-control-group">
              <div className="speed-header">
                <div className="speed-title"><ScrollText size={17} /><span>Số lần cuộn trang</span></div>
                <span className="speed-value">{scrolls}</span>
              </div>
              <input type="range" min="0" max={status?.max_scrolls || 30} step="1" value={scrolls}
                id="nf-scrolls" className="speed-slider" disabled={isBusy}
                onChange={(e) => setScrolls(parseInt(e.target.value, 10))} />
              <p className="nf-hint">Mỗi lần cuộn nghỉ ngẫu nhiên 2.5–5 giây. Càng nhiều càng dễ bị captcha.</p>
            </div>

            <div className="nf-option-row">
              <label className="checkbox-control nf-check">
                <input type="checkbox" id="nf-translate" checked={translateEnabled} disabled={isBusy}
                  onChange={(e) => setTranslateEnabled(e.target.checked)} />
                <span className="checkbox-label-group"><Languages size={15} /> Dịch kết quả sang tiếng Việt</span>
              </label>

              <div className="nf-select-wrap">
                <Cpu size={15} />
                <select id="nf-model" value={model} disabled={isBusy} onChange={(e) => setModel(e.target.value)}>
                  {(status?.ollama_models?.length ? status.ollama_models : [model || status?.default_model || 'qwen2.5:7b'])
                    .map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>

            <div className="nf-option-row">
              <label className="checkbox-control nf-check">
                <input type="checkbox" id="nf-wait-captcha" checked={waitCaptcha} disabled={isBusy}
                  onChange={(e) => setWaitCaptcha(e.target.checked)} />
                <span className="checkbox-label-group"><ShieldAlert size={15} /> Chờ tôi giải captcha (2 phút)</span>
              </label>
              <label className="checkbox-control nf-check">
                <input type="checkbox" id="nf-headless" checked={headless} disabled={isBusy}
                  onChange={(e) => setHeadless(e.target.checked)} />
                <span className="checkbox-label-group"><EyeOff size={15} /> Chạy trình duyệt ẩn</span>
              </label>
            </div>
          </div>

          {/* Hành động / tiến trình */}
          {isBusy ? (
            <div className="progress-status-container nf-progress">
              <div className="progress-status-header">
                <div className="progress-status-title">
                  <Loader2 size={18} className="spin-icon" />
                  <span>{progress?.message || 'Đang xử lý...'}</span>
                </div>
                <span className="progress-percent-badge">{progress?.percent || 0}%</span>
              </div>
              <div className="progress-bar-track">
                <div className="progress-bar-fill" style={{ width: `${Math.max(4, progress?.percent || 0)}%` }}>
                  <div className="progress-shimmer" />
                </div>
              </div>
              {progress?.chunk && (
                <div className="progress-chunk-snippet">
                  <span className="snippet-label">Đang dịch:</span>
                  <span className="snippet-text">"{progress.chunk}"</span>
                </div>
              )}
              <button type="button" className="nf-btn-cancel" onClick={handleCancel} id="nf-cancel">
                <Square size={14} /> Huỷ
              </button>
            </div>
          ) : (
            <div className="nf-actions">
              <button type="button" className="nf-btn-secondary" onClick={handleLogin} id="nf-login">
                <LogIn size={17} /> {loggedIn ? 'Đăng nhập lại' : 'Đăng nhập Zhihu'}
              </button>
              <button type="button" className="btn-synthesize nf-btn-search" onClick={handleSearch}
                disabled={!genres.length && !genreInput.trim()} id="nf-search">
                <Search size={19} /> <span>Tìm truyện</span>
              </button>
            </div>
          )}

          {error && !isBusy && (
            <div className="nf-alert error">
              <ShieldAlert size={16} />
              <span>{error.message}</span>
            </div>
          )}
        </div>

        {/* Log */}
        <div className="card nf-log-card">
          <div className="card-header">
            <div className="card-title-group">
              <Terminal size={18} className="card-header-icon" />
              <h2 className="card-title">Nhật ký</h2>
            </div>
            {logs.length > 0 && (
              <button type="button" className="btn-text-action" onClick={() => setLogs([])}>
                <X size={14} /> Xoá
              </button>
            )}
          </div>
          <div className="nf-log-list">
            {logs.length === 0 && <p className="nf-log-empty">Chưa có hoạt động nào.</p>}
            {logs.map((l, i) => {
              const Icon = LOG_ICONS[l.level] || Info;
              return (
                <div key={i} className={`nf-log-line ${l.level}`}>
                  <span className="nf-log-time">{l.time}</span>
                  <Icon size={13} />
                  <span className="nf-log-msg">{l.message}</span>
                </div>
              );
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      </section>

      {/* ============ Cột phải: kết quả ============ */}
      <section className="column-right">
        <div className="card nf-results-card">
          <div className="card-header">
            <div className="card-title-group">
              <Search size={20} className="card-header-icon highlight" />
              <h2 className="card-title">Kết quả</h2>
              {result && <span className="nf-count-badge">{filteredResults.length}/{result.count}</span>}
            </div>
            {result && (
              <div className="nf-export-group">
                <a className="nf-btn-export" href={getZhihuExportUrl(result.job_id, 'csv')} id="nf-export-csv">
                  <FileSpreadsheet size={15} /> CSV
                </a>
                <a className="nf-btn-export" href={getZhihuExportUrl(result.job_id, 'json')} id="nf-export-json">
                  <FileJson size={15} /> JSON
                </a>
              </div>
            )}
          </div>

          {result ? (
            <>
              <div className="nf-results-toolbar">
                <div className="nf-filter">
                  <Search size={14} />
                  <input id="nf-filter" value={filter} onChange={(e) => setFilter(e.target.value)}
                    placeholder="Lọc trong kết quả..." />
                </div>
                <div className="nf-lang-toggle" role="group">
                  <button type="button" className={!showOriginal ? 'active' : ''} onClick={() => setShowOriginal(false)}>
                    Tiếng Việt
                  </button>
                  <button type="button" className={showOriginal ? 'active' : ''} onClick={() => setShowOriginal(true)}>
                    中文
                  </button>
                </div>
              </div>
              <div className="nf-results-list">
                {filteredResults.map((it, i) => (
                  <ResultCard key={it.link || i} item={it} index={i} showOriginal={showOriginal} />
                ))}
                {filteredResults.length === 0 && <p className="nf-log-empty">Không có kết quả khớp bộ lọc.</p>}
              </div>
            </>
          ) : (
            <div className="placeholder-content nf-placeholder">
              <div className="placeholder-pulse">
                {running === 'search'
                  ? <Loader2 size={36} className="placeholder-icon spin-icon" />
                  : <BookMarked size={36} className="placeholder-icon" />}
              </div>
              <h3>{running === 'search' ? 'Đang tìm truyện...' : 'Chưa có kết quả'}</h3>
              <p>
                {running === 'search'
                  ? 'Có thể mất vài phút. Theo dõi tiến trình ở khung Nhật ký bên trái.'
                  : 'Nhập thể loại, bấm "Đăng nhập Zhihu" (lần đầu) rồi bấm "Tìm truyện". Kết quả được sắp xếp theo lượt tán thành.'}
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
