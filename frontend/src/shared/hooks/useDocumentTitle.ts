import { useEffect } from "react";

export const useDocumentTitle = (title: string, appName = "Prompster") => {
  useEffect(() => {
    const previous = document.title;
    document.title = title ? `${title} – ${appName}` : appName;
    return () => {
      document.title = previous;
    };
  }, [title, appName]);
};
