import { useState, useRef, useCallback } from 'react';
import { getUploadUrl } from '../api/sessionApi';

/**
 * Hook for recording the interview session (screen + mic).
 * Uses the browser MediaRecorder API to record screen and camera separately.
 * Uploads the final recordings to Azure Blob via SAS URLs.
 */
export function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const screenRecorderRef = useRef(null);
  const cameraRecorderRef = useRef(null);
  const screenChunksRef = useRef([]);
  const cameraChunksRef = useRef([]);
  const streamsRef = useRef([]);

  const startRecording = useCallback(async () => {
    setError(null);
    screenChunksRef.current = [];
    cameraChunksRef.current = [];

    try {
      // Get screen stream (video + audio if available)
      let screenStream;
      try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
      } catch (screenErr) {
        console.warn('Screen capture declined or unavailable:', screenErr.message);
      }

      // Get camera stream (video + audio)
      let cameraStream;
      try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
      } catch (micErr) {
        console.warn('Camera/Microphone access denied:', micErr.message);
        setError('Microphone/Camera access is required for the interview.');
        return;
      }

      if (screenStream) streamsRef.current.push(screenStream);
      if (cameraStream) streamsRef.current.push(cameraStream);

      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm';

      if (screenStream) {
        const screenRecorder = new MediaRecorder(screenStream, { mimeType });
        screenRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) screenChunksRef.current.push(e.data);
        };
        screenRecorder.start(1000);
        screenRecorderRef.current = screenRecorder;
      }

      if (cameraStream) {
        const cameraRecorder = new MediaRecorder(cameraStream, { mimeType });
        cameraRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) cameraChunksRef.current.push(e.data);
        };
        cameraRecorder.start(1000);
        cameraRecorderRef.current = cameraRecorder;
      }

      setIsRecording(true);
      console.log(`Recording started. Screen: ${!!screenStream}, Camera: ${!!cameraStream}`);
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError(`Recording failed: ${err.message}`);
    }
  }, []);

  const uploadBlob = async (blob, sessionId, type) => {
    if (!blob || blob.size === 0) return '';
    let retries = 3;
    while (retries > 0) {
      try {
        const uploadInfo = await getUploadUrl(sessionId, type);
        const { sas_url, blob_name } = uploadInfo;
        await fetch(sas_url, {
          method: 'PUT',
          headers: {
            'x-ms-blob-type': 'BlockBlob',
            'Content-Type': blob.type,
          },
          body: blob,
        });
        return blob_name;
      } catch (uploadErr) {
        if (uploadErr.message && uploadErr.message.includes('500')) return '';
        retries--;
        if (retries === 0) return '';
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    return '';
  };

  const stopRecordingAndUpload = useCallback(
    async (sessionId) => {
      return new Promise((resolve) => {
        setIsRecording(false);

        const stopAndGetBlob = (recorder, chunksRef) => {
          return new Promise((r) => {
            if (!recorder || recorder.state === 'inactive') {
              r(chunksRef.current.length ? new Blob(chunksRef.current, { type: 'video/webm' }) : null);
              return;
            }
            recorder.onstop = () => {
              const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' });
              r(blob);
            };
            recorder.stop();
          });
        };

        Promise.all([
          stopAndGetBlob(screenRecorderRef.current, screenChunksRef),
          stopAndGetBlob(cameraRecorderRef.current, cameraChunksRef)
        ]).then(async ([screenBlob, cameraBlob]) => {
          streamsRef.current.forEach((stream) => {
            stream.getTracks().forEach((track) => track.stop());
          });
          streamsRef.current = [];

          const [screenBlobName, cameraBlobName] = await Promise.all([
            uploadBlob(screenBlob, sessionId, 'screen'),
            uploadBlob(cameraBlob, sessionId, 'camera')
          ]);

          resolve({ screenBlobName, cameraBlobName });
        });
      });
    },
    []
  );

  return {
    isRecording,
    error,
    startRecording,
    stopRecordingAndUpload,
  };
}

