// Tự động nhận diện host theo trình duyệt (localhost hoặc 127.0.0.1)
const getInitialBaseUrl = () => {
  if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000';
  }
  return 'http://localhost:8000';
};

export let API_BASE_URL = getInitialBaseUrl();

const getFullUrl = (path) => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
};

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (res.ok) {
      return await res.json();
    }
  } catch (error) {
    const fallbackUrl = API_BASE_URL.includes('localhost')
      ? 'http://127.0.0.1:8000'
      : 'http://localhost:8000';
    try {
      const fallbackRes = await fetch(`${fallbackUrl}/api/health`);
      if (fallbackRes.ok) {
        API_BASE_URL = fallbackUrl;
        return await fallbackRes.json();
      }
    } catch {
      // Offline
    }
    console.error('Health check error:', error);
    return { status: 'offline', error: error.message };
  }
}

// ==================== TTS APIs ====================

export async function synthesizeText(text, speed = 1.0) {
  const cleanText = String(text || '').trim();
  const numSpeed = typeof speed === 'number' ? speed : parseFloat(speed) || 1.0;

  const res = await fetch(`${API_BASE_URL}/api/tts/synthesize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: cleanText, speed: numSpeed }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Lỗi không xác định khi tạo giọng nói' }));
    let errorMsg = 'Lỗi server';
    if (typeof errorData.detail === 'string') {
      errorMsg = errorData.detail;
    } else if (Array.isArray(errorData.detail)) {
      errorMsg = errorData.detail.map((e) => `${e.loc?.slice(1).join('.') || 'Trường'}: ${e.msg}`).join(', ');
    }
    throw new Error(errorMsg);
  }

  const data = await res.json();
  return {
    ...data,
    fullAudioUrl: getFullUrl(data.audio_url),
    fullDownloadUrl: getFullUrl(data.download_url),
  };
}

export async function synthesizeTextStream(text, speed = 1.0, onProgress) {
  const cleanText = String(text || '').trim();
  const numSpeed = typeof speed === 'number' ? speed : parseFloat(speed) || 1.0;

  const res = await fetch(`${API_BASE_URL}/api/tts/synthesize-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: cleanText, speed: numSpeed }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Lỗi kết nối máy chủ' }));
    throw new Error(errorData.detail || 'Lỗi server');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalResult = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.slice(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.type === 'progress' && onProgress) {
            onProgress(payload);
          } else if (payload.type === 'complete') {
            finalResult = payload.result;
          } else if (payload.type === 'error') {
            throw new Error(payload.message || 'Lỗi khi xử lý giọng nói');
          }
        } catch (e) {
          if (e.message.includes('xử lý giọng nói')) throw e;
          console.warn('Stream JSON parse error:', e);
        }
      }
    }
  }

  if (!finalResult) {
    throw new Error('Không nhận được dữ liệu hoàn chỉnh từ server');
  }

  return {
    ...finalResult,
    fullAudioUrl: getFullUrl(finalResult.audio_url),
    fullDownloadUrl: getFullUrl(finalResult.download_url),
  };
}

export async function fetchHistory() {
  const res = await fetch(`${API_BASE_URL}/api/tts/history`);
  if (!res.ok) throw new Error('Không thể tải lịch sử');
  const items = await res.json();
  return items.map((item) => ({
    ...item,
    fullAudioUrl: getFullUrl(item.audio_url),
    fullDownloadUrl: getFullUrl(item.download_url),
  }));
}

export async function deleteHistoryItem(id) {
  const res = await fetch(`${API_BASE_URL}/api/tts/history/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Không thể xóa bản ghi');
  return await res.json();
}

// ==================== Multi-Video Processing APIs ====================

export async function dubVideo(
  videoFiles,
  audioFile = null,
  audioId = null,
  bgmFile = null,
  bgmVolume = 0.2,
  removeOriginalAudio = true,
  durationMode = 'full_video'
) {
  const formData = new FormData();

  const filesArray = Array.isArray(videoFiles) ? videoFiles : [videoFiles];
  for (const file of filesArray) {
    formData.append('videos', file);
  }

  if (audioFile) {
    formData.append('audio_file', audioFile);
  } else if (audioId) {
    formData.append('audio_id', audioId);
  }

  if (bgmFile) {
    formData.append('bgm_file', bgmFile);
    formData.append('bgm_volume', bgmVolume.toString());
  }

  formData.append('remove_original_audio', removeOriginalAudio ? 'true' : 'false');
  formData.append('duration_mode', durationMode);

  const res = await fetch(`${API_BASE_URL}/api/video/dub`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Lỗi khi xử lý video' }));
    throw new Error(errorData.detail || 'Lỗi server');
  }

  const data = await res.json();
  return {
    ...data,
    fullVideoUrl: getFullUrl(data.video_url),
    fullDownloadUrl: getFullUrl(data.download_url),
  };
}

export async function fetchVideoHistory() {
  const res = await fetch(`${API_BASE_URL}/api/video/history`);
  if (!res.ok) throw new Error('Không thể tải lịch sử video');
  const items = await res.json();
  return items.map((item) => ({
    ...item,
    fullVideoUrl: getFullUrl(item.video_url),
    fullDownloadUrl: getFullUrl(item.download_url),
  }));
}

export async function deleteVideoHistoryItem(id) {
  const res = await fetch(`${API_BASE_URL}/api/video/history/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Không thể xóa video');
  return await res.json();
}
