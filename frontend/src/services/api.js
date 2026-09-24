const API_BASE_URL = 'http://127.0.0.1:8000';

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
