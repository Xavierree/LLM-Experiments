"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function TrainingPanel() {
    const [status, setStatus] = React.useState("idle")

    const startTraining = async () => {
        setStatus("training")
        try {
            const res = await fetch("http://localhost:8000/api/train", { method: "POST" })
            if (res.ok) {
                // The backend returns immediately, but the process takes time.
                // We'll keep the "training" status for a bit or maybe introduce a "running" state?
                // For now, let's just alert or log. The backend handles the background task.
            }
        } catch (e) {
            console.error(e)
            setStatus("idle")
        }
    }

    return (
        <Card className="w-full max-w-md">
            <CardHeader>
                <CardTitle>LoRA Fine-Tuning</CardTitle>
                <CardDescription>Train Qwen and Mistral on latest logs.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex justify-between text-sm">
                    <span>Mistral Dataset:</span>
                    <span className="font-mono">~1.4M samples</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span>Qwen Dataset:</span>
                    <span className="font-mono">Chat History</span>
                </div>

                {status === "training" && (
                    <div className="p-2 bg-yellow-500/10 text-yellow-500 rounded text-sm text-center animate-pulse">
                        Training in progress... check terminal
                    </div>
                )}
            </CardContent>
            <CardFooter>
                <Button onClick={startTraining} disabled={status === "training"} className="w-full">
                    {status === "training" ? "Training..." : "Start Training Pipeline"}
                </Button>
            </CardFooter>
        </Card>
    )
}
