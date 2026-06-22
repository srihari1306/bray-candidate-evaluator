const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const getSession = (id) => {
  const search = window.location.search;
  return fetch(`${BASE}/interview/session/${id}${search}`).then((r) => {
    if (!r.ok) throw new Error(`Session fetch failed: ${r.status}`);
    return r.json();
  });
};

export const getSpeechToken = () => {
  const search = window.location.search;
  return fetch(`${BASE}/interview/speech-token${search}`).then((r) => {
    if (!r.ok) throw new Error(`Speech token fetch failed: ${r.status}`);
    return r.json();
  });
};

export const getUploadUrl = (id, type = 'screen') => {
  const params = new URLSearchParams(window.location.search);
  params.set('type', type);
  return fetch(`${BASE}/interview/upload-url/${id}?${params.toString()}`).then(async (r) => {
    if (!r.ok) {
      let errText = '';
      try {
        errText = await r.text();
      } catch (e) {}
      throw new Error(`Upload URL fetch failed: ${r.status} - ${errText}`);
    }
    return r.json();
  });
};

export const submitAnswers = (payload) => {
  const params = new URLSearchParams(window.location.search);
  const exp = params.get('exp') || '';
  const sig = params.get('sig') || '';
  
  return fetch(`${BASE}/interview/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, exp, sig }),
  }).then((r) => {
    if (!r.ok) throw new Error(`Answer submission failed: ${r.status}`);
    return r.json();
  });
};
