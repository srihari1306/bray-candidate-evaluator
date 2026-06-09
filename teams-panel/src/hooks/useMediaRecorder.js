import { useState, useRef, useCallback } from 'react';
import { getUploadUrl } from '../api/sessionApi';

/**
 * Hook for recording the interview session (screen + mic).
 * Uses the browser MediaRecorder API.
 * Uploads the final recording to Azure Blob via SAS URL.
 */
export function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamsRef = useRef([]);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      // Get screen stream
      let screenStream;
      try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false,
        });
      } catch (screenErr) {
        console.warn('Screen capture declined or unavailable:', screenErr.message);
        // Continue without screen — audio only
      }

      // Get microphone stream
      let micStream;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: false,
        });
      } catch (micErr) {
        console.warn('Microphone access denied:', micErr.message);
        setError('Microphone access is required for the interview.');
        return;
      }

      // Combine tracks
      const tracks = [];
      if (screenStream) {
        screenStream.getVideoTracks().forEach((t) => tracks.push(t));
        streamsRef.current.push(screenStream);
      }
      if (micStream) {
        micStream.getAudioTracks().forEach((t) => tracks.push(t));
        streamsRef.current.push(micStream);
      }

      const combinedStream = new MediaStream(tracks);

      // Determine MIME type (video/webm for screen+mic, audio/webm for mic only)
      let mimeType = 'video/webm;codecs=vp8,opus';
      if (!screenStream) {
        mimeType = 'audio/webm;codecs=opus';
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/webm';
        }
      }

      const recorder = new MediaRecorder(combinedStream, { mimeType });

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setError('Recording error occurred.');
      };

      recorder.start(1000); // Collect chunks every second
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      console.log(`Recording started with MIME type: ${mimeType}`);
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError(`Recording failed: ${err.message}`);
    }
  }, []);

  const stopRecordingAndUpload = useCallback(
    async (sessionId) => {
      return new Promise(async (resolve, reject) => {
        if (!mediaRecorderRef.current) {
          resolve('');
          return;
        }

        const recorder = mediaRecorderRef.current;

        recorder.onstop = async () => {
          setIsRecording(false);
          console.log('[useMediaRecorder] Recorder stopped.');

          // Stop all streams
          streamsRef.current.forEach((stream) => {
            stream.getTracks().forEach((track) => track.stop());
          });
          streamsRef.current = [];

          // Create blob from chunks
          const blob = new Blob(chunksRef.current, {
            type: recorder.mimeType || 'video/webm',
          });
          chunksRef.current = [];
          console.log(`[useMediaRecorder] Blob created. Size: ${blob.size} bytes. MIME Type: ${blob.type || recorder.mimeType || 'video/webm'}`);

          if (blob.size === 0) {
            console.warn('[useMediaRecorder] Recording blob is empty');
            resolve('');
            return;
          }

          console.log(`[useMediaRecorder] Recording complete: ${(blob.size / 1024 / 1024).toFixed(2)} MB`);

          // Upload to Azure Blob via SAS URL
          let retries = 3;
          while (retries > 0) {
            try {
              console.log(`[useMediaRecorder] Calling getUploadUrl for sessionId: ${sessionId}`);
              const uploadInfo = await getUploadUrl(sessionId);
              console.log('[useMediaRecorder] getUploadUrl completed successfully. Response:', uploadInfo);

              const { sas_url, blob_name } = uploadInfo;

              console.log(`[useMediaRecorder] Uploading blob to SAS URL via PUT: ${blob_name}`);
              await fetch(sas_url, {
                method: 'PUT',
                headers: {
                  'x-ms-blob-type': 'BlockBlob',
                  'Content-Type': recorder.mimeType || 'video/webm',
                },
                body: blob,
              });

              console.log(`[useMediaRecorder] ✓ PUT to SAS URL completed successfully. Recording uploaded: ${blob_name}`);
              resolve(blob_name);
              return;
            } catch (uploadErr) {
              console.error('[useMediaRecorder] Upload encountered an error:', uploadErr);

              // If getUploadUrl returns a 500, log and abort immediately with empty string
              if (uploadErr.message && uploadErr.message.includes('500')) {
                console.error('[useMediaRecorder] getUploadUrl failed with 500 error. Aborting upload.');
                resolve('');
                return;
              }

              retries--;
              console.error(`[useMediaRecorder] Upload attempt failed (${retries} retries left):`, uploadErr);
              if (retries === 0) {
                setError('Failed to upload recording after 3 attempts.');
                resolve(''); // Don't reject — don't block the interview flow
              }
              await new Promise((r) => setTimeout(r, 2000));
            }
          }
        };

        recorder.stop();
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
