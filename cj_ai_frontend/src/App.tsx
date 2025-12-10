import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import Index from "./pages/Index";
import PressReleasePage from "./pages/PressReleasePage";
import TranslatorPage from "./pages/TranslatorPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Index />} />        
        <Route path="/press-release" element={<PressReleasePage />} />
        <Route path="/translator" element={<TranslatorPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;