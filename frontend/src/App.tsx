import { Routes, Route } from "react-router-dom";
import { VerificationPage } from "./pages/VerificationPage";
import { ManufacturerPage } from "./pages/ManufacturerPage";
import { AdminDashboard } from "./pages/AdminDashboard";
import { Layout } from "./components/Layout";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<VerificationPage />} />
        <Route path="manufacturer" element={<ManufacturerPage />} />
        <Route path="admin" element={<AdminDashboard />} />
      </Route>
    </Routes>
  );
}

export default App;