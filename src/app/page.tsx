import Link from "next/link";

export default function Home() {
  return (
    <div className="container">
      <main>
        <div className="hero">
          <span className="badge">Local Intelligence v2.0</span>
          <h1 className="title">Neural Orchestrator</h1>
          <p className="subtitle">
            Advanced control interface for local LLM pipelines including Mistral, Qwen, and RAG workflows.
          </p>
          <Link href="/cockpit">
            <button>Launch Cockpit</button>
          </Link>
        </div>

        <div className="grid">
          <div className="card">
            <h2>🤖 Model Manager</h2>
            <p>
              Load and fine-tune local models.
              <br />
              <span style={{ color: '#4ade80' }}>● Active: Mistral-7B-Instruct</span>
            </p>
          </div>



          <div className="card">
            <h2>⚡ Training Logs</h2>
            <p>
              Monitor LoRA training sessions and loss curves.
              <br />
              <span style={{ color: '#a78bfa' }}>● Last Run: 2.94 loss</span>
            </p>
          </div>

          <div className="card">
            <h2>💬 Playground</h2>
            <p>
              Interactive chat session with context-aware retrieval.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
