import { msg } from "@lit/localize";
let loadPromise: Promise<typeof Spotify> | null = null;

export const loadSpotifySdk = (): Promise<typeof Spotify> => {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Spotify SDK can only run in the browser."));
  }

  if (window.Spotify) {
    return Promise.resolve(window.Spotify);
  }

  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise((resolve, reject) => {
    window.onSpotifyWebPlaybackSDKReady = () => {
      if (!window.Spotify) {
        reject(new Error("Spotify SDK loaded without Spotify global."));
        return;
      }
      resolve(window.Spotify);
    };

    const script = document.createElement("script");
    script.src = "https://sdk.scdn.co/spotify-player.js";
    script.async = true;
    script.onerror = () => {
      loadPromise = null;
      reject(new Error(msg("Der Spotify-Player konnte nicht geladen werden.")));
    };

    document.body.appendChild(script);
  });

  return loadPromise;
};
