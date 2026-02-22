"use client";

import { useState, useEffect, useRef } from "react";
import RefinementControl from "@/components/RefinementControl";

// Types matching backend
interface Turn {
    id: string;
    prompt: string;
    status: "pending" | "accepted";
    iterations: Iteration[];
    final_output: string | null;
}

interface Iteration {
    index: number;
    response: string;
    correction: string | null;
    timestamp: number;
}

interface Session {
    id: string;
    turns: Turn[];
}

export default function Cockpit() {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [history, setHistory] = useState<Turn[]>([]);
    const [currentTurn, setCurrentTurn] = useState<Turn | null>(null);

    const [input, setInput] = useState("");
    const [selectedModel, setSelectedModel] = useState("chat");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    // Initialize Session
    useEffect(() => {
        const initSession = async () => {
            try {
                const res = await fetch("http://localhost:8000/api/sessions", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title: "Refinement Session" })
                });
                const data = await res.json();
                setSessionId(data.id);
            } catch (err) {
                console.error("Failed to init session", err);
            }
        };
        initSession();
    }, []);

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history, currentTurn, loading]);

    const startTurn = async () => {
        if (!input.trim() || !sessionId) return;
        setLoading(true);

        // Optimistic UI? No, wait for generation.
        // Ideally we stream, but simple fetch for now.

        try {
            const res = await fetch("http://localhost:8000/api/chat/turn/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, prompt: input, model: selectedModel })
            });
            const turn: Turn = await res.json();
            setCurrentTurn(turn);
            setInput("");
        } catch (e) {
            console.error(e);
            alert("Error starting turn");
        } finally {
            setLoading(false);
        }
    };

    const refineTurn = async (correction: string) => {
        if (!sessionId || !currentTurn) return;
        setLoading(true);

        try {
            const res = await fetch("http://localhost:8000/api/chat/turn/refine", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, correction })
            });
            const updatedTurn: Turn = await res.json();
            setCurrentTurn(updatedTurn);
        } catch (e) {
            console.error(e);
            alert("Error refining turn");
        } finally {
            setLoading(false);
        }
    };

    const acceptTurn = async () => {
        if (!sessionId || !currentTurn) return;

        try {
            await fetch("http://localhost:8000/api/chat/turn/accept", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId })
            });

            // Update history locally or re-fetch?
            // Local check:
            const accepted = { ...currentTurn, status: "accepted" as const, final_output: currentTurn.iterations[currentTurn.iterations.length - 1].response };
            setHistory(prev => [...prev, accepted]);
            setCurrentTurn(null);
        } catch (e) {
            console.error(e);
        }
    };

    if (!sessionId) return <div className="flex h-screen items-center justify-center text-white">Initializing Cockpit...</div>;

    return (
        <div className="flex flex-col h-screen bg-black text-white font-sans">
            <header className="p-4 border-b border-gray-800 bg-gray-900 flex justify-between items-center">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    Refinement Cockpit
                </h1>
                <div className="text-xs text-gray-500 font-mono">{sessionId.slice(0, 8)}</div>
            </header>

            <main className="flex-1 overflow-y-auto p-4 space-y-6">
                {/* History of Completed Turns */}
                {history.map((turn) => (
                    <div key={turn.id} className="opacity-75">
                        <div className="flex justify-end mb-2">
                            <div className="bg-blue-900/40 px-4 py-2 rounded-2xl rounded-tr-none max-w-[80%]">
                                <p className="text-sm">{turn.prompt}</p>
                            </div>
                        </div>
                        <div className="flex justify-start">
                            <div className="bg-gray-800/60 px-4 py-2 rounded-2xl rounded-tl-none max-w-[80%]">
                                <p className="text-sm whitespace-pre-wrap">{turn.final_output}</p>
                                <div className="mt-1 text-xs text-green-500">✓ Verified after {turn.iterations.length} iterations</div>
                            </div>
                        </div>
                    </div>
                ))}

                {/* Current Active Turn */}
                {currentTurn && (
                    <div className="border border-blue-500/30 rounded-lg p-4 bg-blue-900/10">
                        <div className="flex justify-end mb-4">
                            <div className="bg-blue-600 px-4 py-2 rounded-2xl rounded-tr-none max-w-[80%]">
                                <p className="text-sm">{currentTurn.prompt}</p>
                            </div>
                        </div>

                        {currentTurn.iterations.map((iter, idx) => (
                            <div key={idx} className="mb-4">
                                <div className="flex justify-start">
                                    <div className={`px-4 py-2 rounded-2xl rounded-tl-none max-w-[90%] ${idx === currentTurn.iterations.length - 1 ? 'bg-gray-800 text-white' : 'bg-gray-800/50 text-gray-400'}`}>
                                        <p className="text-sm whitespace-pre-wrap">{iter.response}</p>
                                    </div>
                                </div>
                                {iter.correction && (
                                    <div className="my-2 flex justify-center">
                                        <span className="text-xs text-yellow-500 bg-yellow-900/20 px-2 py-1 rounded">
                                            Correction: {iter.correction}
                                        </span>
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Controls for the latest response */}
                        <RefinementControl
                            onAccept={acceptTurn}
                            onRefine={refineTurn}
                            isProcessing={loading}
                        />
                    </div>
                )}

                {/* Loading State for New Turn */}
                {loading && !currentTurn && (
                    <div className="flex justify-center text-blue-400 animate-pulse text-sm">Generating initial response...</div>
                )}

                <div ref={bottomRef} />
            </main>

            {/* Input Area (Only visible when no active turn) */}
            {!currentTurn && (
                <footer className="p-4 border-t border-gray-800 bg-gray-900">
                    <div className="flex gap-2 max-w-4xl mx-auto">
                        <select
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-3 text-white focus:border-blue-500 outline-none text-sm"
                        >
                            <option value="chat">Chat (Qwen 7B)</option>
                            <option value="general">General (Qwen 14B)</option>
                            <option value="code">Code (DeepSeek 6.7B)</option>
                            <option value="planner">Planner (Qwen 7B)</option>
                            <option value="executioner">Executioner (Qwen 14B)</option>
                            <option value="synthesis">Synthesis (Qwen 32B)</option>
                        </select>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && startTurn()}
                            placeholder="Enter a prompt to start a refinement session..."
                            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-white"
                            disabled={loading}
                        />
                        <button
                            onClick={startTurn}
                            disabled={loading || !input.trim()}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            Start
                        </button>
                    </div>
                </footer>
            )}
        </div>
    );
}
