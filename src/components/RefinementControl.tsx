"use client";

import { useState } from "react";

interface RefinementControlProps {
    onAccept: () => void;
    onRefine: (correction: string) => void;
    isProcessing: boolean;
}

export default function RefinementControl({ onAccept, onRefine, isProcessing }: RefinementControlProps) {
    const [isRejecting, setIsRejecting] = useState(false);
    const [correction, setCorrection] = useState("");

    const handleRefine = () => {
        if (!correction.trim()) return;
        onRefine(correction);
        setCorrection("");
        setIsRejecting(false); // Reset UI state after refinement triggers
    };

    if (isProcessing) {
        return <div className="p-4 text-center text-gray-400 animate-pulse">Thinking...</div>;
    }

    return (
        <div className="mt-4 p-4 border border-gray-700 rounded-lg bg-gray-900/50">
            <h3 className="text-sm font-medium text-gray-300 mb-2">Verdict?</h3>

            {!isRejecting ? (
                <div className="flex gap-4">
                    <button
                        onClick={onAccept}
                        className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded text-white text-sm font-semibold transition-colors flex-1"
                    >
                        ✅ Accept
                    </button>
                    <button
                        onClick={() => setIsRejecting(true)}
                        className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded text-white text-sm font-semibold transition-colors flex-1"
                    >
                        ❌ Reject & Refine
                    </button>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    <textarea
                        value={correction}
                        onChange={(e) => setCorrection(e.target.value)}
                        placeholder="How should this be improved?"
                        className="w-full p-2 bg-black border border-gray-600 rounded text-white text-sm focus:border-blue-500 outline-none"
                        rows={3}
                    />
                    <div className="flex gap-2 justify-end">
                        <button
                            onClick={() => setIsRejecting(false)}
                            className="px-3 py-1 text-gray-400 hover:text-gray-200 text-sm"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleRefine}
                            disabled={!correction.trim()}
                            className="px-4 py-1 bg-blue-600 hover:bg-blue-500 rounded text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Submit Correction
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
