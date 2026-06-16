const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const getSession = (id) =>
  fetch(`${BASE}/interview/session/${id}`).then((r) => {
    if (!r.ok) throw new Error(`Session fetch failed: ${r.status}`);
    return r.json();
  });

export const getSpeechToken = () =>
  fetch(`${BASE}/interview/speech-token`).then((r) => {
    if (!r.ok) throw new Error(`Speech token fetch failed: ${r.status}`);
    return r.json();
  });

export const getUploadUrl = (id, type = 'screen') =>
  fetch(`${BASE}/interview/upload-url/${id}?type=${type}`).then(async (r) => {
    console.log(`[getUploadUrl API] type: ${type}, status: ${r.status}`);
    if (!r.ok) {
      let errText = '';
      try {
        errText = await r.text();
      } catch (e) {}
      console.log(`[getUploadUrl API] error response: ${errText}`);
      throw new Error(`Upload URL fetch failed: ${r.status} - ${errText}`);
    }
    const data = await r.json();
    console.log(`[getUploadUrl API] full response:`, data);
    return data;
  });

export const submitAnswers = (payload) =>
  fetch(`${BASE}/interview/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then((r) => {
    if (!r.ok) throw new Error(`Answer submission failed: ${r.status}`);
    return r.json();
  });
