import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import PressRelease from './pages/PressRelease'
import ElectionLaw from './pages/ElectionLaw'
import NewsViewer from './pages/NewsViewer'
import NotFound from './pages/NotFound'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/press-release" element={<PressRelease />} />
        <Route path="/election-law" element={<ElectionLaw />} />
        <Route path="/news" element={<NewsViewer />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  )
}

export default App
