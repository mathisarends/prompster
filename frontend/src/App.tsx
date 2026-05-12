import { Navigate, Route, Routes } from "react-router-dom";
import { InteractiveDeckPage } from "./pages/InteractiveDeckPage";
import { HomePage } from "./pages/HomePage";

export const App = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/deck/new" element={<HomePage />} />
      <Route path="/deck/mock" element={<InteractiveDeckPage />} />
      <Route path="*" element={<Navigate to="/deck/new" replace />} />
    </Routes>
  );
};
