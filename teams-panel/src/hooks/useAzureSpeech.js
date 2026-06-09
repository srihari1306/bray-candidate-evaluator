import { useState, useRef, useCallback } from 'react';
import { getSpeechToken } from '../api/sessionApi';

/**
 * Hook wrapping the Azure Speech SDK for real-time speech-to-text.
 * Fetches a short-lived token from the backend and uses continuous recognition.
 *
 * For standalone testing (outside Teams), uses the browser's built-in
 * SpeechRecognition API as a fallback when the Azure SDK is not available.
 */
export function useAzureSpeech() {
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const recognizerRef = useRef(null);
  const browserRecognitionRef = useRef(null);

  const startRecognition = useCallback(async () => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);
    setIsRecording(true);

    // Try Azure Speech SDK first
    try {
      const SpeechSDK = await import('microsoft-cognitiveservices-speech-sdk');
      const tokenData = await getSpeechToken();

      const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(
        tokenData.token,
        tokenData.region
      );
      speechConfig.speechRecognitionLanguage = 'en-US';

      const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

      recognizer.recognizing = (_, e) => {
        // Interim results — show live feedback
        if (e.result.text) {
          setInterimTranscript(e.result.text);
        }
      };

      recognizer.recognized = (_, e) => {
        if (e.result.text) {
          setTranscript((prev) => {
            const trimmed = prev.trim();
            return trimmed ? `${trimmed} ${e.result.text}` : e.result.text;
          });
          setInterimTranscript('');
        }
      };

      recognizer.canceled = (_, e) => {
        console.warn('Speech recognition canceled:', e.reason);
        if (e.reason === SpeechSDK.CancellationReason.Error) {
          setError(`Recognition error: ${e.errorDetails}`);
        }
      };

      recognizer.startContinuousRecognitionAsync(
        () => console.log('Azure Speech recognition started'),
        (err) => {
          console.error('Failed to start recognition:', err);
          setError('Failed to start speech recognition');
          setIsRecording(false);
        }
      );

      recognizerRef.current = recognizer;
      return;
    } catch (sdkError) {
      console.warn('Azure Speech SDK not available, using browser fallback:', sdkError.message);
    }

    // Fallback: Browser Web Speech API
    try {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        throw new Error('No speech recognition available');
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      let finalTranscript = '';

      recognition.onresult = (event) => {
        let interim = '';
        let newlyFinalized = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            newlyFinalized += event.results[i][0].transcript + ' ';
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        if (newlyFinalized) {
          finalTranscript += newlyFinalized;
          setTranscript(finalTranscript.trim());
        }
        setInterimTranscript(interim.trim());
      };

      recognition.onerror = (event) => {
        console.error('Browser speech recognition error:', event.error);
        if (event.error !== 'aborted') {
          setError(`Speech recognition error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        // Auto-restart if still recording
        if (browserRecognitionRef.current) {
          try {
            recognition.start();
          } catch {
            // Already ended
          }
        }
      };

      recognition.start();
      browserRecognitionRef.current = recognition;
    } catch (fallbackError) {
      setError('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      setIsRecording(false);
    }
  }, []);

  const stopRecognition = useCallback(() => {
    setIsRecording(false);

    // Stop Azure SDK recognizer
    if (recognizerRef.current) {
      recognizerRef.current.stopContinuousRecognitionAsync(
        () => {
          recognizerRef.current.close();
          recognizerRef.current = null;
        },
        (err) => console.error('Error stopping recognition:', err)
      );
    }

    // Stop browser recognition
    if (browserRecognitionRef.current) {
      const ref = browserRecognitionRef.current;
      browserRecognitionRef.current = null;
      try {
        ref.stop();
      } catch {
        // Already stopped
      }
    }

    return transcript;
  }, [transcript]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);
  }, []);

  return {
    transcript,
    interimTranscript,
    isRecording,
    error,
    startRecognition,
    stopRecognition,
    resetTranscript,
  };
}
