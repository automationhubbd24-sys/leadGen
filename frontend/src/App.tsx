import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './Dashboard.tsx';
import Instructions from './Instructions';
import './App.css';

const App: React.FC = () => {
    return (
        <Router>
            <div className="app-container">
                <nav className="top-nav">
                    <h1>LeadGen Bot</h1>
                    <div>
                        <Link to="/dashboard" className="nav-link">Dashboard</Link>
                        <Link to="/docs" className="nav-link">Docs</Link>
                    </div>
                </nav>
                <main>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/dashboard" element={<Dashboard />} />
                        <Route path="/docs" element={<Instructions />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
};

export default App;
