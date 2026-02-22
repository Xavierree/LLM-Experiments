"use client"

import * as React from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Sparkles, Loader2 } from "lucide-react"

export function RefineryPanel() {
    const [status, setStatus] = React.useState("idle")

    const startRefining = async () => {
        setStatus("processing")
        try {
            const res = await fetch("http://localhost:8000/api/refine", { method: "POST" })
            if (res.ok) {
                // Poll or just wait? For now just show "Started"
                setTimeout(() => setStatus("done"), 3000)
            }
        } catch (e) {
            console.error(e)
            setStatus("error")
        }
    }

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-purple-500" />
                    Data Refinery
                </CardTitle>
                <CardDescription>
                    Clean and verify chat logs using Groq API before training.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-2 text-sm text-muted-foreground">
                    <p>• Extract Qwen, Mistral, Llama2, CodeLlama, & DeepSeek datasets</p>
                    <p>• Verify quality with Llama3-70b (Groq)</p>
                    <p>• Output: <code>verified_&lt;model&gt;.jsonl</code></p>
                </div>
            </CardContent>
            <CardFooter>
                <Button
                    onClick={startRefining}
                    disabled={status === "processing"}
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600"
                >
                    {status === "processing" ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Refining...
                        </>
                    ) : status === "done" ? (
                        "Refinement Started!"
                    ) : (
                        "Start Refinery Pipeline"
                    )}
                </Button>
            </CardFooter>
        </Card>
    )
}
