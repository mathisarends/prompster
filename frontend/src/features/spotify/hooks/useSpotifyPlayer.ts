import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { isAxiosError } from "axios";

import { fetchSpotifyAccessToken } from "@/features/spotify/lib/spotify-token";
import { loadSpotifySdk } from "@/features/spotify/lib/spotify-sdk";

const PLAYER_NAME = "Prompster Web Player";
const INITIAL_VOLUME = 0.72;

type SpotifyPlayerStatus =
  | "idle"
  | "loading"
  | "ready"
  | "premium-required"
  | "auth-error"
  | "error";

type PlaybackClockState = {
  positionMs: number;
  durationMs: number;
  capturedAtMs: number;
  paused: boolean;
};

type SpotifyDevice = {
  id: string | null;
  name: string;
  is_active: boolean;
};

type SpotifyDevicesResponse = {
  devices?: SpotifyDevice[];
};

export type SpotifyPlayerState = {
  status: SpotifyPlayerStatus;
  deviceId: string | null;
  isPaused: boolean;
  positionMs: number;
  durationMs: number;
  currentTrackUri: string | null;
};

type UseSpotifyPlayerOptions = {
  enabled?: boolean;
};

const INITIAL_STATE: SpotifyPlayerState = {
  status: "idle",
  deviceId: null,
  isPaused: true,
  positionMs: 0,
  durationMs: 0,
  currentTrackUri: null,
};

const createInitialClockState = (): PlaybackClockState => ({
  positionMs: 0,
  durationMs: 0,
  capturedAtMs: performance.now(),
  paused: true,
});

const isConnectRequiredError = (error: unknown): boolean => {
  if (!isAxiosError(error)) {
    return false;
  }

  return error.response?.status === 409 || error.response?.status === 410;
};

const clampMs = (value: number, max: number): number => {
  if (max <= 0) {
    return Math.max(0, value);
  }
  return Math.max(0, Math.min(value, max));
};

const pickPreferredDeviceId = (
  payload: SpotifyDevicesResponse,
): string | null => {
  const devices = payload.devices ?? [];

  const namedDevice = devices.find(
    (device) => device.id && device.name === PLAYER_NAME,
  );
  if (namedDevice?.id) {
    return namedDevice.id;
  }

  const activeDevice = devices.find((device) => device.id && device.is_active);
  if (activeDevice?.id) {
    return activeDevice.id;
  }

  const fallbackDevice = devices.find((device) => Boolean(device.id));
  return fallbackDevice?.id ?? null;
};

export const useSpotifyPlayer = (options: UseSpotifyPlayerOptions = {}) => {
  const { enabled = true } = options;
  const [state, setState] = useState<SpotifyPlayerState>(INITIAL_STATE);
  const playerRef = useRef<Spotify.Player | null>(null);
  const deviceIdRef = useRef<string | null>(null);
  const clockRef = useRef<PlaybackClockState>(createInitialClockState());
  const rafRef = useRef<number | null>(null);

  const setStatus = useCallback((status: SpotifyPlayerStatus) => {
    setState((previous) => ({ ...previous, status }));
  }, []);

  const setConnectRequired = useCallback(() => {
    deviceIdRef.current = null;
    setState((previous) => ({
      ...previous,
      status: "auth-error",
      deviceId: null,
      isPaused: true,
      positionMs: 0,
      durationMs: 0,
      currentTrackUri: null,
    }));
    clockRef.current = {
      positionMs: 0,
      durationMs: 0,
      capturedAtMs: performance.now(),
      paused: true,
    };
  }, []);

  useEffect(() => {
    deviceIdRef.current = state.deviceId;
  }, [state.deviceId]);

  useEffect(() => {
    if (!enabled) {
      playerRef.current?.disconnect();
      playerRef.current = null;
      deviceIdRef.current = null;
      queueMicrotask(() => {
        setState(INITIAL_STATE);
      });
      return;
    }

    let disposed = false;

    queueMicrotask(() => {
      setStatus("loading");
    });

    const initialize = async () => {
      try {
        const SpotifySdk = await loadSpotifySdk();
        if (disposed) return;

        const player = new SpotifySdk.Player({
          name: PLAYER_NAME,
          volume: INITIAL_VOLUME,
          getOAuthToken: (callback) => {
            void fetchSpotifyAccessToken()
              .then((accessToken) => callback(accessToken))
              .catch((error) => {
                if (isConnectRequiredError(error)) {
                  setConnectRequired();
                  return;
                }
                setStatus("auth-error");
              });
          },
        });

        const onReady = ({ device_id }: Spotify.WebPlaybackInstance) => {
          deviceIdRef.current = device_id;
          setState((previous) => ({
            ...previous,
            status: "ready",
            deviceId: device_id,
          }));
        };

        const onNotReady = ({ device_id }: Spotify.WebPlaybackInstance) => {
          if (deviceIdRef.current === device_id) {
            deviceIdRef.current = null;
          }

          setState((previous) => ({
            ...previous,
            deviceId:
              previous.deviceId === device_id ? null : previous.deviceId,
          }));
        };

        const onPlayerStateChanged = (
          playbackState: Spotify.PlaybackState | null,
        ) => {
          if (!playbackState) return;

          const nextPositionMs = clampMs(
            playbackState.position,
            playbackState.duration,
          );

          clockRef.current = {
            positionMs: nextPositionMs,
            durationMs: playbackState.duration,
            capturedAtMs: performance.now(),
            paused: playbackState.paused,
          };

          const currentTrack = playbackState.track_window.current_track;
          // Spotify relinks tracks to market-specific equivalents, so the SDK
          // can report a different URI than the one we requested. `linked_from`
          // carries the originally requested URI; prefer it so the reported
          // track keeps matching the URI stored on our playlist tracks.
          const reportedTrackUri =
            currentTrack?.linked_from?.uri ?? currentTrack?.uri ?? null;

          setState((previous) => ({
            ...previous,
            status:
              previous.status === "premium-required"
                ? previous.status
                : "ready",
            isPaused: playbackState.paused,
            positionMs: nextPositionMs,
            durationMs: playbackState.duration,
            currentTrackUri: reportedTrackUri,
          }));
        };

        const onInitializationError = () => setStatus("error");
        const onAuthenticationError = () => setStatus("auth-error");
        const onAccountError = () => setStatus("premium-required");
        const onPlaybackError = () => setStatus("error");

        player.addListener("ready", onReady);
        player.addListener("not_ready", onNotReady);
        player.addListener("player_state_changed", onPlayerStateChanged);
        player.addListener("initialization_error", onInitializationError);
        player.addListener("authentication_error", onAuthenticationError);
        player.addListener("account_error", onAccountError);
        player.addListener("playback_error", onPlaybackError);

        playerRef.current = player;

        const connected = await player.connect();
        if (!connected) {
          setStatus("error");
        }

        if (disposed) {
          player.disconnect();
          return;
        }
      } catch {
        setStatus("error");
      }
    };

    void initialize();

    return () => {
      disposed = true;
      playerRef.current?.disconnect();
      playerRef.current = null;
      deviceIdRef.current = null;
    };
  }, [enabled, setConnectRequired, setStatus]);

  useEffect(() => {
    const tick = () => {
      const clock = clockRef.current;

      if (!clock.paused) {
        const elapsedMs = performance.now() - clock.capturedAtMs;
        const nextPositionMs = clampMs(
          clock.positionMs + elapsedMs,
          clock.durationMs,
        );

        setState((previous) => {
          if (previous.isPaused || previous.status !== "ready") {
            return previous;
          }

          if (Math.abs(nextPositionMs - previous.positionMs) < 250) {
            return previous;
          }

          return {
            ...previous,
            positionMs: nextPositionMs,
          };
        });
      }

      rafRef.current = window.requestAnimationFrame(tick);
    };

    rafRef.current = window.requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, []);

  const playTrack = useCallback(
    async (uri: string): Promise<void> => {
      let accessToken: string;

      try {
        accessToken = await fetchSpotifyAccessToken();
      } catch (error) {
        if (isConnectRequiredError(error)) {
          setConnectRequired();
          return;
        }
        setStatus("auth-error");
        throw error;
      }

      const resolveDeviceId = async (
        forceRefresh = false,
      ): Promise<string | null> => {
        if (!forceRefresh && playerRef.current && deviceIdRef.current) {
          return deviceIdRef.current;
        }

        let response = await fetch(
          "https://api.spotify.com/v1/me/player/devices",
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          },
        );

        if (response.status === 401) {
          accessToken = await fetchSpotifyAccessToken();
          response = await fetch(
            "https://api.spotify.com/v1/me/player/devices",
            {
              headers: {
                Authorization: `Bearer ${accessToken}`,
              },
            },
          );
        }

        if (!response.ok) {
          return null;
        }

        const payload = (await response.json()) as SpotifyDevicesResponse;
        const resolvedDeviceId = pickPreferredDeviceId(payload);

        if (!resolvedDeviceId) {
          return null;
        }

        deviceIdRef.current = resolvedDeviceId;
        setState((previous) =>
          previous.deviceId === resolvedDeviceId
            ? previous
            : { ...previous, deviceId: resolvedDeviceId },
        );

        return resolvedDeviceId;
      };

      let deviceId = await resolveDeviceId();
      if (!deviceId) {
        throw new Error("Spotify player device is not ready.");
      }

      const sendPlayRequest = async (
        targetDeviceId: string,
      ): Promise<Response> => {
        return fetch(
          `https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(targetDeviceId)}`,
          {
            method: "PUT",
            headers: {
              Authorization: `Bearer ${accessToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ uris: [uri] }),
          },
        );
      };

      let response: Response;

      try {
        let retried401 = false;
        let retried404 = false;

        while (true) {
          response = await sendPlayRequest(deviceId);

          if (response.status === 401 && !retried401) {
            accessToken = await fetchSpotifyAccessToken();
            retried401 = true;
            continue;
          }

          if (response.status === 404 && !retried404) {
            const recoveredDeviceId = await resolveDeviceId(true);
            if (recoveredDeviceId) {
              deviceId = recoveredDeviceId;
            }
            retried404 = true;
            continue;
          }

          break;
        }
      } catch (error) {
        if (isConnectRequiredError(error)) {
          setConnectRequired();
          return;
        }
        setStatus("error");
        throw error;
      }

      if (response.status === 403) {
        setStatus("premium-required");
        return;
      }

      if (!response.ok) {
        setStatus("error");
        throw new Error(
          `Spotify playback failed with status ${response.status}.`,
        );
      }

      setState((previous) => ({
        ...previous,
        status: "ready",
        deviceId,
        isPaused: false,
        currentTrackUri: uri,
      }));
    },
    [setConnectRequired, setStatus],
  );

  const resume = useCallback(async (): Promise<void> => {
    const player = playerRef.current;
    if (!player) return;

    await player.resume();
    setState((previous) => ({ ...previous, isPaused: false }));
    clockRef.current = {
      ...clockRef.current,
      positionMs: state.positionMs,
      durationMs: state.durationMs,
      capturedAtMs: performance.now(),
      paused: false,
    };
  }, [state.durationMs, state.positionMs]);

  const pause = useCallback(async (): Promise<void> => {
    const player = playerRef.current;
    if (!player) return;

    await player.pause();
    setState((previous) => ({ ...previous, isPaused: true }));
    clockRef.current = {
      ...clockRef.current,
      positionMs: state.positionMs,
      durationMs: state.durationMs,
      capturedAtMs: performance.now(),
      paused: true,
    };
  }, [state.durationMs, state.positionMs]);

  const seek = useCallback(
    async (ms: number): Promise<void> => {
      const player = playerRef.current;
      if (!player) return;

      const boundedMs = clampMs(ms, state.durationMs);
      await player.seek(boundedMs);

      setState((previous) => ({ ...previous, positionMs: boundedMs }));
      clockRef.current = {
        ...clockRef.current,
        positionMs: boundedMs,
        durationMs: state.durationMs,
        capturedAtMs: performance.now(),
        paused: state.isPaused,
      };
    },
    [state.durationMs, state.isPaused],
  );

  const setVolume = useCallback(async (value: number): Promise<void> => {
    const player = playerRef.current;
    if (!player) return;

    const bounded = Math.max(0, Math.min(value, 1));
    await player.setVolume(bounded);
  }, []);

  return useMemo(
    () => ({
      state,
      playTrack,
      resume,
      pause,
      seek,
      setVolume,
    }),
    [pause, playTrack, resume, seek, setVolume, state],
  );
};
