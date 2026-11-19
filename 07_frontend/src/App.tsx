import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";

import { DiagnosisProvider } from "./context/DiagnosisContext";
import { AppShell } from "./layouts/AppShell";
import { PublicLayout } from "./layouts/PublicLayout";
import { DiagnosisPage } from "./pages/DiagnosisPage";
import { DiagnosisResultPage } from "./pages/DiagnosisResultPage";
import { DiseaseDetailPage } from "./pages/DiseaseDetailPage";
import { HomePage } from "./pages/HomePage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { NotFoundPage } from "./pages/NotFoundPage";

function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash !== "") {
      const target = document.querySelector(hash);
      if (target instanceof HTMLElement) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  }, [pathname, hash]);

  return null;
}

export default function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ScrollToTop />
      <DiagnosisProvider>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route index element={<HomePage />} />
            <Route path="knowledge-base" element={<KnowledgeBasePage />} />
            <Route path="knowledge-base/:id" element={<DiseaseDetailPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
          <Route element={<AppShell />}>
            <Route path="diagnosis" element={<DiagnosisPage />} />
            <Route path="diagnosis/result" element={<DiagnosisResultPage />} />
          </Route>
        </Routes>
      </DiagnosisProvider>
    </BrowserRouter>
  );
}
