import { Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Recruitment from "./pages/Recruitment";
import Performance from "./pages/Performance";
import TalentRisk from "./pages/TalentRisk";
import OrgHealth from "./pages/OrgHealth";
import StrategicReport from "./pages/StrategicReport";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/recruitment" element={<Recruitment />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/talent-risk" element={<TalentRisk />} />
        <Route path="/org-health" element={<OrgHealth />} />
        <Route path="/report" element={<StrategicReport />} />
      </Routes>
    </Layout>
  );
}

export default App;
