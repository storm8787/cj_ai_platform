import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewsViewer from './pages/NewsViewer';
import PressRelease from './pages/PressRelease';
import ElectionLaw from './pages/ElectionLaw';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/news" element={<NewsViewer />} />
        <Route path="/press-release" element={<PressRelease />} />
        <Route path="/election-law" element={<ElectionLaw />} />
      </Routes>
    </Layout>
  );
}

export default App;