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

  loadPromise = new Promise<typeof Spotify>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://sdk.scdn.co/spotify-player.js";
    script.async = true;
    window.onSpotifyWebPlaybackSDKReady = () => {
      if (!window.Spotify) {
        script.remove();
        reject(new Error("Spotify SDK loaded without Spotify global."));
        return;
      }
      resolve(window.Spotify);
    };
    script.onerror = () => {
      script.remove();
      reject(new Error("Spotify SDK failed to load."));
    };
    document.body.appendChild(script);
  }).catch((error: unknown) => {
    loadPromise = null;
    throw error;
  });

  return loadPromise;
};
