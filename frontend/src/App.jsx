import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Investigation from './pages/Investigation';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <nav style={{ padding: '1rem', borderBottom: '1px solid #ccc' }}>
          <Link to="/" style={{ marginRight: '1rem' }}>
            Dashboard
          </Link>
          <Link to="/investigation">Investigation</Link>
        </nav>

        <div style={{ padding: '2rem' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/investigation" element={<Investigation />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
