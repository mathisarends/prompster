import { useCallback, useEffect, useRef, useState } from "react";

import {
  parseTranscriptionEvent,
  resolveTranscriptionWebSocketUrl,
  TranscriptionServerEventType,
  type TranscriptionServerEvent,
} from "@/api/transcription-stream";

const TARGET_SAMPLE_RATE = 24_000;
const AUDIO_BUFFER_SIZE = 4096;
const STOP_TIMEOUT_MS = 900;

type AudioContextConstructor = typeof AudioContext;
type StartErrorReason = "microphone" | "websocket" | "audio";

type RealtimeTranscriptionStatus =
  | "idle"
  | "requesting_permission"
  | "connecting"
  | "recording";

type UseRealtimeTranscriptionOptions = {
  value: string;
  onTranscriptChange: (value: string) => void;
  disabled?: boolean;
};

const toPcm16 = (
  input: Float32Array,
  sourceSampleRate: number,
): ArrayBuffer => {
  const sampleRateRatio = sourceSampleRate / TARGET_SAMPLE_RATE;
  const outputLength = Math.max(1, Math.floor(input.length / sampleRateRatio));
  const buffer = new ArrayBuffer(outputLength * 2);
  const view = new DataView(buffer);

  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = Math.min(
      input.length - 1,
      Math.floor(index * sampleRateRatio),
    );
    const sample = Math.max(-1, Math.min(1, input[sourceIndex] ?? 0));
    view.setInt16(
      index * 2,
      sample < 0 ? sample * 0x8000 : sample * 0x7fff,
      true,
    );
  }

  return buffer;
};

const getAudioContextConstructor = (): AudioContextConstructor | undefined => {
  return (
    window.AudioContext ??
    (window as Window & { webkitAudioContext?: AudioContextConstructor })
      .webkitAudioContext
  );
};

const isRetryableMicrophoneStartError = (error: unknown): boolean => {
  return (
    error instanceof DOMException &&
    (error.name === "OverconstrainedError" || error.name === "NotReadableError")
  );
};

const getMicrophoneErrorMessage = (error: unknown): string => {
  if (!(error instanceof DOMException)) {
    return "Mikrofon konnte nicht gestartet werden.";
  }

  switch (error.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Mikrofonzugriff wurde vom Browser oder Betriebssystem blockiert.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "Kein Mikrofon gefunden.";
    case "NotReadableError":
    case "TrackStartError":
      return "Mikrofon ist gerade nicht verfuegbar oder wird von einer anderen App verwendet.";
    case "OverconstrainedError":
      return "Mikrofon unterstuetzt die angefragten Audioeinstellungen nicht.";
    default:
      return `Mikrofon konnte nicht gestartet werden (${error.name}).`;
  }
};

const requestMicrophoneStream = async (): Promise<MediaStream> => {
  try {
    return await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: { ideal: 1 },
        echoCancellation: { ideal: true },
        noiseSuppression: { ideal: true },
        autoGainControl: { ideal: true },
      },
    });
  } catch (error) {
    if (!isRetryableMicrophoneStartError(error)) {
      throw error;
    }

    return navigator.mediaDevices.getUserMedia({ audio: true });
  }
};

export const useRealtimeTranscription = ({
  value,
  onTranscriptChange,
  disabled = false,
}: UseRealtimeTranscriptionOptions) => {
  const [status, setStatus] = useState<RealtimeTranscriptionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const valueRef = useRef(value);
  const baseTextRef = useRef("");
  const transcriptItemsRef = useRef(new Map<string, string>());
  const websocketRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  const clearStopTimeout = useCallback(() => {
    if (stopTimeoutRef.current === null) return;
    window.clearTimeout(stopTimeoutRef.current);
    stopTimeoutRef.current = null;
  }, []);

  const closeAudio = useCallback(async () => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    silentGainRef.current?.disconnect();

    processorRef.current = null;
    sourceRef.current = null;
    silentGainRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;

    const audioContext = audioContextRef.current;
    audioContextRef.current = null;
    if (audioContext && audioContext.state !== "closed") {
      await audioContext.close();
    }
  }, []);

  const closeSocket = useCallback(() => {
    const websocket = websocketRef.current;
    websocketRef.current = null;
    if (!websocket || websocket.readyState === WebSocket.CLOSED) return;

    if (websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({ type: "stop" }));
    }
    websocket.close();
  }, []);

  const stop = useCallback(async () => {
    clearStopTimeout();
    await closeAudio();

    const websocket = websocketRef.current;
    if (websocket?.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({ type: "flush" }));
      stopTimeoutRef.current = window.setTimeout(() => {
        closeSocket();
        setStatus("idle");
      }, STOP_TIMEOUT_MS);
      return;
    }

    closeSocket();
    setStatus("idle");
  }, [clearStopTimeout, closeAudio, closeSocket]);

  const renderTranscript = useCallback(() => {
    const transcript = Array.from(transcriptItemsRef.current.values())
      .join(" ")
      .replace(/\s+/g, " ")
      .trimStart();
    const baseText = baseTextRef.current;
    const separator = baseText.trim() && transcript ? " " : "";
    onTranscriptChange(`${baseText}${separator}${transcript}`);
  }, [onTranscriptChange]);

  const handleEvent = useCallback(
    (event: TranscriptionServerEvent) => {
      switch (event.type) {
        case TranscriptionServerEventType.TranscriptDelta: {
          const current = transcriptItemsRef.current.get(event.itemId) ?? "";
          transcriptItemsRef.current.set(event.itemId, current + event.delta);
          renderTranscript();
          break;
        }
        case TranscriptionServerEventType.TranscriptCompleted:
          transcriptItemsRef.current.set(event.itemId, event.transcript);
          renderTranscript();
          break;
        case TranscriptionServerEventType.TranscriberError:
          setError(event.error.message);
          break;
        case TranscriptionServerEventType.Error:
          setError(event.message);
          break;
        case TranscriptionServerEventType.SessionConnected:
        case TranscriptionServerEventType.SpeechStarted:
        case TranscriptionServerEventType.SpeechStopped:
          break;
      }
    },
    [renderTranscript],
  );

  const start = useCallback(async () => {
    if (disabled || status !== "idle") return;

    const AudioContextCtor = getAudioContextConstructor();
    if (!AudioContextCtor || !navigator.mediaDevices?.getUserMedia) {
      setError("Spracheingabe wird in diesem Browser nicht unterstuetzt.");
      return;
    }

    setError(null);
    setStatus("connecting");
    baseTextRef.current = valueRef.current;
    transcriptItemsRef.current = new Map();

    let startErrorReason: StartErrorReason = "websocket";
    let startError: unknown = null;

    try {
      const websocketUrl = resolveTranscriptionWebSocketUrl();
      const websocket = new WebSocket(websocketUrl);
      websocket.binaryType = "arraybuffer";
      websocketRef.current = websocket;

      await new Promise<void>((resolve, reject) => {
        let settled = false;

        websocket.onopen = () => {
          settled = true;
          resolve();
        };
        websocket.onerror = () => {
          if (settled) return;
          settled = true;
          reject(new Error("Transcription websocket failed"));
        };
        websocket.onclose = () => {
          if (settled) return;
          settled = true;
          reject(new Error("Transcription websocket closed before open"));
        };
      });

      setStatus("requesting_permission");
      startErrorReason = "microphone";
      const mediaStream = await requestMicrophoneStream();
      mediaStreamRef.current = mediaStream;

      startErrorReason = "audio";
      const audioContext = new AudioContextCtor();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(mediaStream);
      const processor = audioContext.createScriptProcessor(
        AUDIO_BUFFER_SIZE,
        1,
        1,
      );
      const silentGain = audioContext.createGain();
      silentGain.gain.value = 0;

      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioContext.destination);

      sourceRef.current = source;
      processorRef.current = processor;
      silentGainRef.current = silentGain;

      processor.onaudioprocess = (event) => {
        const socket = websocketRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN) return;

        const input = event.inputBuffer.getChannelData(0);
        socket.send(toPcm16(input, audioContext.sampleRate));
      };

      websocket.onmessage = (event) => {
        if (typeof event.data !== "string") return;
        handleEvent(parseTranscriptionEvent(event.data));
      };
      websocket.onclose = () => {
        clearStopTimeout();
        void closeAudio();
        setStatus("idle");
      };
      websocket.onerror = () => {
        setError("Verbindung zur Transkription wurde unterbrochen.");
      };

      setStatus("recording");
    } catch (error) {
      startError = error;
      console.error("Realtime transcription failed to start", error);
      await closeAudio();
      closeSocket();
      if (startErrorReason === "microphone") {
        setError(getMicrophoneErrorMessage(startError));
      } else if (startErrorReason === "audio") {
        setError("Audioaufnahme konnte nicht gestartet werden.");
      } else {
        setError("Transkriptionsdienst ist nicht erreichbar.");
      }
      setStatus("idle");
    }
  }, [
    clearStopTimeout,
    closeAudio,
    closeSocket,
    disabled,
    handleEvent,
    status,
  ]);

  useEffect(() => {
    return () => {
      clearStopTimeout();
      void closeAudio();
      closeSocket();
    };
  }, [clearStopTimeout, closeAudio, closeSocket]);

  return {
    error,
    isRecording: status === "recording",
    isStarting: status === "requesting_permission" || status === "connecting",
    start,
    stop,
  };
};
