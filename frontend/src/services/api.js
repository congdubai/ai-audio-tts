function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1' || !host) {
      return 'http://127.0.0.1:8000';
    }
    return `http://${host}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

const API_BASE_URL = getApiBaseUrl();

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) throw new Error('Không thể kết nối đến server backend');
    return await res.json();
  } catch (error) {
    console.error('Health check error:', error);
    return { status: 'offline', error: error.message };
  }
}

// ==================== TTS APIs ====================

export async function synthesizeText(text, speed = 1.0) {
  const res = await fetch(`${API_BASE_URL}/api/tts/synthesize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, speed }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Lỗi không xác định khi tạo giọng nói' }));
    throw new Error(errorData.detail || 'Lỗi server');
  }

  const data = await res.json();
  return {
    ...data,
    fullAudioUrl: `${API_BASE_URL}${data.audio_url}`,
    fullDownloadUrl: `${API_BASE_URL}${data.download_url}`,
  };
}

export async function fetchHistory() {
  const res = await fetch(`${API_BASE_URL}/api/tts/history`);
  if (!res.ok) throw new Error('Không thể tải lịch sử');
  const items = await res.json();
  return items.map((item) => ({
    ...item,
    fullAudioUrl: `${API_BASE_URL}${item.audio_url}`,
    fullDownloadUrl: `${API_BASE_URL}${item.download_url}`,
  }));
}

export async function deleteHistoryItem(id) {
  const res = await fetch(`${API_BASE_URL}/api/tts/history/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Không thể xóa bản ghi');
  return await res.json();
}

// ==================== Multi-Video Dubbing APIs ====================

export async function dubVideo(videoFiles, text, speed = 1.0, removeOriginalAudio = true, durationMode = 'full_video') {
  const formData = new FormData();
  
  const filesArray = Array.isArray(videoFiles) ? videoFiles : [videoFiles];
  for (const file of filesArray) {
    formData.append('videos', file);
  }

  formData.append('text', text);
  formData.append('speed', speed.toString());
  formData.append('remove_original_audio', removeOriginalAudio ? 'true' : 'false');
  formData.append('duration_mode', durationMode);

  const res = await fetch(`${API_BASE_URL}/api/video/dub`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Lỗi khi xử lý lồng tiếng video' }));
    throw new Error(errorData.detail || 'Lỗi server');
  }

  const data = await res.json();
  return {
    ...data,
    fullVideoUrl: `${API_BASE_URL}${data.video_url}`,
    fullDownloadUrl: `${API_BASE_URL}${data.download_url}`,
  };
}

export async function fetchVideoHistory() {
  const res = await fetch(`${API_BASE_URL}/api/video/history`);
  if (!res.ok) throw new Error('Không thể tải lịch sử video');
  const items = await res.json();
  return items.map((item) => ({
    ...item,
    fullVideoUrl: `${API_BASE_URL}${item.video_url}`,
    fullDownloadUrl: `${API_BASE_URL}${item.download_url}`,
  }));
}

export async function deleteVideoHistoryItem(id) {
  const res = await fetch(`${API_BASE_URL}/api/video/history/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Không thể xóa video');
  return await res.json();
}
