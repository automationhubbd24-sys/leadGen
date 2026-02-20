import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = "http://127.0.0.1:8080/api";

const Dashboard: React.FC = () => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [status, setStatus] = useState('');
    const [masterSheetId, setMasterSheetId] = useState('');

    useEffect(() => {
        // This is a mock check. In a real app, you'd verify the session with the backend.
        const creds = sessionStorage.getItem('userCredentials');
        if (creds) {
            setIsLoggedIn(true);
        }
    }, []);

    const handleLogin = () => {
        axios.get(`${API_URL}/login`)
            .then(response => {
                window.location.href = response.data.authorization_url;
            })
            .catch(error => {
                setStatus('Login failed: ' + error.message);
            });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('Starting campaign... This may take a long time.');
        axios.post(`${API_URL}/start-multi-campaign`, { masterSheetId }, { withCredentials: true })
            .then(response => {
                setStatus(response.data.status);
            })
            .catch(error => {
                setStatus('Error: ' + (error.response?.data?.error || error.message));
            });
    };

    if (!isLoggedIn) {
        // A simple check for the redirect from OAuth
        if (window.location.pathname.includes('/dashboard')) {
            setIsLoggedIn(true);
            sessionStorage.setItem('userCredentials', 'true'); // Mock session storage
        } else {
            return (
                <div className="dashboard">
                    <h2>Welcome to LeadGen Bot</h2>
                    <p>Please log in with your Google Account to continue.</p>
                    <button onClick={handleLogin} className="login-button">Login with Google</button>
                </div>
            );
        }
    }

    return (
        <div className="dashboard">
            <h2>Multi-Account Campaign</h2>
            <p>Enter the Master Google Sheet ID to start the full campaign across all accounts.</p>
            <form onSubmit={handleSubmit} className="campaign-form">
                <input
                    type="text"
                    value={masterSheetId}
                    onChange={(e) => setMasterSheetId(e.target.value)}
                    placeholder="Enter Master Google Sheet ID"
                    required
                />
                <button type="submit">Start Full Campaign</button>
            </form>
            {status && <p className="status-message">{status}</p>}
        </div>
    );
};

export default Dashboard;
