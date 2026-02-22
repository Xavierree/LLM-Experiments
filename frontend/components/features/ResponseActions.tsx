"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { CheckCircle2, XCircle, Send } from "lucide-react"

interface ResponseActionsProps {
    onAccept: () => void
    onReject: (correction: any) => void
    isProcessing: boolean
    mode?: string
}

export function ResponseActions({ onAccept, onReject, isProcessing, mode }: ResponseActionsProps) {
    const [showCorrection, setShowCorrection] = React.useState(false)
    const [correction, setCorrection] = React.useState("")

    // Agent Inputs
    const [plannerCorr, setPlannerCorr] = React.useState("")
    const [executorCorr, setExecutorCorr] = React.useState("")
    const [synthesisCorr, setSynthesisCorr] = React.useState("")

    const handleReject = () => {
        setShowCorrection(true)
    }

    const handleSubmitCorrection = () => {
        if (mode === 'agent') {
            // Send object
            onReject({
                planner: plannerCorr,
                executor: executorCorr,
                synthesis: synthesisCorr
            })
        } else {
            if (!correction.trim()) return
            onReject(correction)
        }
        setCorrection("")
        setPlannerCorr("")
        setExecutorCorr("")
        setSynthesisCorr("")
        setShowCorrection(false)
    }

    const handleCancel = () => {
        setShowCorrection(false)
        setCorrection("")
    }

    if (isProcessing) {
        return (
            <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
                <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                Generating response...
            </div>
        )
    }

    if (!showCorrection) {
        return (
            <div className="flex items-center gap-2 mt-3">
                <Button
                    size="sm"
                    variant="default"
                    onClick={onAccept}
                    className="gap-2"
                >
                    <CheckCircle2 className="h-4 w-4" />
                    Accept
                </Button>
                <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    className="gap-2"
                >
                    <XCircle className="h-4 w-4" />
                    Reject & Refine
                </Button>
            </div>
        )
    }

    return (
        <div className="mt-3 space-y-2">
            {mode === 'agent' ? (
                <div className="space-y-3">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Refine Agent Stages</p>

                    <div className="space-y-1">
                        <label className="text-xs text-indigo-400">Planner Correction</label>
                        <textarea
                            value={plannerCorr}
                            onChange={(e) => setPlannerCorr(e.target.value)}
                            placeholder="Wrong steps? Missing objective?"
                            className="w-full h-[60px] p-2 border border-indigo-500/20 bg-indigo-500/5 rounded-md resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500 text-xs"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-xs text-blue-400">Executor Correction</label>
                        <textarea
                            value={executorCorr}
                            onChange={(e) => setExecutorCorr(e.target.value)}
                            placeholder="Code error? Wrong command?"
                            className="w-full h-[60px] p-2 border border-blue-500/20 bg-blue-500/5 rounded-md resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-xs text-purple-400">Synthesis Correction</label>
                        <textarea
                            value={synthesisCorr}
                            onChange={(e) => setSynthesisCorr(e.target.value)}
                            placeholder="Bad summary? Missing details?"
                            className="w-full h-[60px] p-2 border border-purple-500/20 bg-purple-500/5 rounded-md resize-none focus:outline-none focus:ring-1 focus:ring-purple-500 text-xs"
                        />
                    </div>
                </div>
            ) : (
                <textarea
                    value={correction}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCorrection(e.target.value)}
                    placeholder="What should be different? Be specific..."
                    className="w-full min-h-[80px] p-2 border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                    autoFocus
                    onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                        if (e.key === "Enter" && e.metaKey) {
                            handleSubmitCorrection()
                        }
                    }}
                />
            )}
            <div className="flex gap-2">
                <Button
                    size="sm"
                    onClick={handleSubmitCorrection}
                    disabled={mode === 'agent' ? (!plannerCorr && !executorCorr && !synthesisCorr) : !correction.trim()}
                    className="gap-2"
                >
                    <Send className="h-4 w-4" />
                    Submit Correction
                </Button>
                <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCancel}
                >
                    Cancel
                </Button>
            </div>
        </div>
    )
}
