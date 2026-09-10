import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { JobsPage } from "./pages/JobsPage";
import { MaterialsPage } from "./pages/MaterialsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StudioPage } from "./pages/StudioPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/projeler" replace />} />
        <Route path="/projeler" element={<ProjectsPage />} />
        <Route path="/studyo/*" element={<StudioPage />} />
        <Route path="/malzemeler" element={<MaterialsPage />} />
        <Route path="/isler" element={<JobsPage />} />
        <Route path="/ayarlar" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/projeler" replace />} />
      </Routes>
    </AppShell>
  );
}
