import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewsViewer from './pages/NewsViewer';
import PressRelease from './pages/PressRelease';
import ElectionLaw from './pages/ElectionLaw';
import MeritReport from './pages/MeritReport';
import DataAnalysis from './pages/DataAnalysis';
import Translator from './pages/Translator';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/news" element={<NewsViewer />} />
        <Route path="/press-release" element={<PressRelease />} />
        <Route path="/election-law" element={<ElectionLaw />} />
        <Route path="/merit-report" element={<MeritReport />} />
        <Route path="/data-analysis" element={<DataAnalysis />} />
        <Route path="/translator" element={<Translator />} />
      </Routes>
    </Layout>
  );
}

export default App;