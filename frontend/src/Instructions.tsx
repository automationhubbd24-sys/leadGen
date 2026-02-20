import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import instructionsMd from './INSTRUCTIONS.md';
import './Instructions.css';

const Instructions: React.FC = () => {
    const [markdown, setMarkdown] = useState('');

    useEffect(() => {
        fetch(instructionsMd)
            .then(response => response.text())
            .then(text => setMarkdown(text));
    }, []);

    return (
        <div className="instructions-container">
            <Link to="/dashboard" className="back-link">← Back to Dashboard</Link>
            <div className="markdown-content">
                <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
        </div>
    );
};

export default Instructions;
