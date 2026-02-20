import React, { useState } from 'react';
import axios from 'axios';

const API_URL = "http://127.0.0.1:8080/api";

const Dashboard: React.FC = () => {
    const [status, setStatus] = useState('');
    const [masterSheetId, setMasterSheetId] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('Starting campaign... This may take a long time. Check the terminal for progress.');
        axios.post(`${API_URL}/start-multi-campaign`, { masterSheetId })
            .then(response => {
                setStatus(response.data.status);
            })
            .catch(error => {
                setStatus('Error: ' + (error.response?.data?.error || error.message));
            });
    };

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
