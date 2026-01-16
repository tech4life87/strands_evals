import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard, ExperimentDetail, NewExperiment } from './pages';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/experiments/new" element={<NewExperiment />} />
          <Route path="/experiments/:id" element={<ExperimentDetail />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
