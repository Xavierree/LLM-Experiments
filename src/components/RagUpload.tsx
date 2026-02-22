'use client';

import { useState } from 'react';

export default function RagUpload() {
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.[0]) return;

        setUploading(true);
        setMessage('');

        // In strict Next.js setups, we need to know the backend URL.
        // For now, we assume proxied or same-origin if configured, or direct localhost:8000
        const API_URL = 'http://localhost:8000/api/ingest';

        const formData = new FormData();
        formData.append('file', e.target.files[0]);

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Upload failed');
            }

            setMessage(`✅ Success: ${data.chunks_added} chunks added.`);
        } catch (err: any) {
            setMessage(`❌ Error: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="card">
            <h2>🧠 RAG Pipeline</h2>
            <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                Refinery & Vector Database Status
                <br />
                <span style={{ color: '#fbbf24' }}>● Ready for Ingestion</span>
            </p>

            <div style={{ marginTop: '1rem' }}>
                <label
                    htmlFor="file-upload"
                    style={{
                        display: 'block',
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px dashed rgba(96, 165, 250, 0.5)',
                        borderRadius: '0.5rem',
                        padding: '1.5rem',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        color: '#60a5fa'
                    }}
                >
                    {uploading ? 'Processing...' : '📄 Upload PDF/DOCX/TXT'}
                </label>
                <input
                    id="file-upload"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleUpload}
                    style={{ display: 'none' }}
                    disabled={uploading}
                />
            </div>

            {message && (
                <p style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>
                    {message}
                </p>
            )}
        </div>
    );
}
