import { useEffect, useReducer } from "react";

import type { PlaylistTrack } from "@/lib/playlist-track";

export type DeckPlaylistController = {
  isPlaying: boolean;
  activeTrackId: string | null;
  positionSeconds: number;
  durationSeconds: number;
  volume: number;
  onPlayTrack: (trackId: string) => void;
  onPause: () => void;
  onResume: () => void;
  onSeek: (seconds: number) => void;
  onVolumeChange: (volume: number) => void;
};

type LocalState = {
  tracks: PlaylistTrack[];
  activeTrackId: string | null;
  isPlaying: boolean;
  remainingSeconds: number;
  durationSeconds: number;
  volume: number;
};

type LocalAction =
  | { type: "ACTIVATE_TRACK"; trackId: string }
  | { type: "REMOVE_TRACK"; trackId: string }
  | { type: "PAUSE" }
  | { type: "RESUME" }
  | { type: "SEEK"; remainingSeconds: number }
  | { type: "SET_VOLUME"; volume: number }
  | { type: "TICK" };

function reducer(state: LocalState, action: LocalAction): LocalState {
  switch (action.type) {
    case "ACTIVATE_TRACK": {
      const track = state.tracks.find((t) => t.id === action.trackId);
      if (!track) return state;
      return {
        ...state,
        activeTrackId: action.trackId,
        remainingSeconds: track.durationSeconds,
        durationSeconds: track.durationSeconds,
        isPlaying: true,
      };
    }
    case "REMOVE_TRACK": {
      const nextTracks = state.tracks.filter((t) => t.id !== action.trackId);
      if (state.activeTrackId !== action.trackId) {
        return { ...state, tracks: nextTracks };
      }
      return {
        ...state,
        tracks: nextTracks,
        activeTrackId: null,
        isPlaying: false,
        remainingSeconds: 0,
        durationSeconds: 0,
      };
    }
    case "PAUSE":
      return { ...state, isPlaying: false };
    case "RESUME":
      return state.activeTrackId ? { ...state, isPlaying: true } : state;
    case "SEEK":
      return { ...state, remainingSeconds: action.remainingSeconds };
    case "SET_VOLUME":
      return { ...state, volume: action.volume };
    case "TICK":
      return state.isPlaying
        ? { ...state, remainingSeconds: Math.max(state.remainingSeconds - 1, 0) }
        : state;
  }
}

export type PlaybackAPI = {
  tracks: PlaylistTrack[];
  activeTrackId: string | null;
  isPlaying: boolean;
  elapsedSeconds: number;
  durationSeconds: number;
  volume: number;
  activateTrack: (trackId: string) => void;
  onPlayPause: () => void;
  onPause: () => void;
  onResume: () => void;
  onSeek: (elapsedSeconds: number) => void;
  onVolumeChange: (volume: number) => void;
  removeTrackFromPlayback: (trackId: string) => void;
};

export function usePlaybackState(
  initialTracks: PlaylistTrack[],
  controller?: DeckPlaylistController,
): PlaybackAPI {
  const [local, dispatch] = useReducer(reducer, {
    tracks: initialTracks,
    activeTrackId: initialTracks[0]?.id ?? null,
    isPlaying: initialTracks.length > 0,
    remainingSeconds: initialTracks[0]?.durationSeconds ?? 0,
    durationSeconds: initialTracks[0]?.durationSeconds ?? 0,
    volume: 72,
  });

  useEffect(() => {
    if (controller || !local.isPlaying || local.activeTrackId === null) return;
    const id = window.setInterval(() => dispatch({ type: "TICK" }), 1000);
    return () => window.clearInterval(id);
  }, [controller, local.isPlaying, local.activeTrackId]);

  if (controller) {
    return {
      tracks: initialTracks,
      activeTrackId: controller.activeTrackId,
      isPlaying: controller.isPlaying,
      elapsedSeconds: controller.positionSeconds,
      durationSeconds: controller.durationSeconds,
      volume: controller.volume,
      activateTrack: controller.onPlayTrack,
      onPlayPause: () =>
        controller.isPlaying ? controller.onPause() : controller.onResume(),
      onPause: controller.onPause,
      onResume: controller.onResume,
      onSeek: controller.onSeek,
      onVolumeChange: controller.onVolumeChange,
      removeTrackFromPlayback: () => {},
    };
  }

  return {
    tracks: local.tracks,
    activeTrackId: local.activeTrackId,
    isPlaying: local.isPlaying,
    elapsedSeconds: Math.max(0, local.durationSeconds - local.remainingSeconds),
    durationSeconds: local.durationSeconds,
    volume: local.volume,
    activateTrack: (trackId) => dispatch({ type: "ACTIVATE_TRACK", trackId }),
    onPlayPause: () => dispatch({ type: local.isPlaying ? "PAUSE" : "RESUME" }),
    onPause: () => dispatch({ type: "PAUSE" }),
    onResume: () => dispatch({ type: "RESUME" }),
    onSeek: (elapsedSeconds) =>
      dispatch({
        type: "SEEK",
        remainingSeconds: local.durationSeconds - elapsedSeconds,
      }),
    onVolumeChange: (volume) => dispatch({ type: "SET_VOLUME", volume }),
    removeTrackFromPlayback: (trackId) =>
      dispatch({ type: "REMOVE_TRACK", trackId }),
  };
}
