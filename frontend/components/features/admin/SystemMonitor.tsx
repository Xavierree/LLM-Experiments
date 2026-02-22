"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { RefreshCw, Terminal, Activity, Zap } from "lucide-react"

export function SystemMonitor() {
    const [status, setStatus] = React.useState<{ current_model: string | null; is_loaded: boolean }>({
        current_model: null,
        is_loaded: false
    })
    const [logs, setLogs] = React.useState<string[]>([])
    const [isConnected, setIsConnected] = React.useState(false)

    // Poll status
    const fetchStatus = React.useCallback(async () => {
        try {
            const res = await fetch("http://localhost:8000/api/system/status")
            const data = await res.json()
            setStatus(data)
        } catch (e) {
            console.error("Failed to fetch status", e)
        }
    }, [])

    React.useEffect(() => {
        fetchStatus()
        // const interval = setInterval(fetchStatus, 5000)
        // return () => clearInterval(interval)
    }, [fetchStatus])

    // WebSocket for Logs
    React.useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/api/ws/system/logs")

        ws.onopen = () => setIsConnected(true)
        ws.onclose = () => setIsConnected(false)

        ws.onmessage = (event) => {
            const message = event.data
            setLogs(prev => [...prev.slice(-999), message])
        }

        return () => ws.close()
    }, [])

    // Auto-scroll
    const logEndRef = React.useRef<HTMLDivElement>(null)
    React.useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [logs])

    const handleReload = async () => {
        await fetch("http://localhost:8000/api/system/reload", { method: "POST" })
        fetchStatus()
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Control Card */}
            <Card className="md:col-span-1 border-white/10 bg-black/20 backdrop-blur-sm">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Activity className="w-5 h-5 text-blue-500" />
                        System Status
                    </CardTitle>
                    <CardDescription>Current Model & Resources</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-2">
                        <div className="text-sm text-muted-foreground">Current Loaded Model</div>
                        <div className="flex items-center justify-between p-3 rounded-lg border bg-background/50">
                            <span className="font-mono font-bold text-lg">
                                {status.current_model || "None"}
                            </span>
                            <Badge variant={status.is_loaded ? "default" : "secondary"}>
                                {status.is_loaded ? "Active" : "Idle"}
                            </Badge>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="text-sm text-muted-foreground">Actions</div>

                        <div className="grid grid-cols-2 gap-2">
                            <Button
                                variant="outline"
                                className="w-full gap-2"
                                onClick={fetchStatus}
                            >
                                <RefreshCw className="w-4 h-4" />
                                Refresh Status
                            </Button>

                            <Button
                                variant="destructive"
                                className="w-full gap-2"
                                onClick={handleReload}
                            >
                                <Zap className="w-4 h-4" />
                                Reload
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Reload unloads the current model from GPU memory.
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Terminal Card */}
            <Card className="md:col-span-2 border-white/10 bg-black/40 backdrop-blur-sm flex flex-col h-[500px]">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <div className="space-y-1">
                        <CardTitle className="flex items-center gap-2">
                            <Terminal className="w-5 h-5 text-green-500" />
                            Terminal Output
                        </CardTitle>
                        <CardDescription>Real-time backend logs</CardDescription>
                    </div>
                    <Badge variant="outline" className={isConnected ? "text-green-500 border-green-500/50" : "text-red-500"}>
                        {isConnected ? "Connected" : "Disconnected"}
                    </Badge>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 pt-0">
                    <div className="h-full bg-black/90 rounded-lg border border-white/10 p-4 font-mono text-sm overflow-y-auto custom-scrollbar">
                        {logs.map((log, i) => (
                            <div key={i} className="text-gray-300 whitespace-pre-wrap break-all border-l-2 border-transparent hover:border-white/20 pl-2">
                                <span className="text-gray-500 select-none mr-2">
                                    {new Date().toLocaleTimeString()}
                                </span>
                                {log}
                            </div>
                        ))}
                        <div ref={logEndRef} />
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
