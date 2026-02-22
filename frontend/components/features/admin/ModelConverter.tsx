"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, HardDrive, ArrowRight, Check } from "lucide-react"

interface ModelItem {
    id: string
    path: string
    is_mlx: boolean
    has_mlx_converted: boolean
    mlx_path?: string
}

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDown } from "lucide-react"

export function ModelConverter() {
    const [models, setModels] = React.useState<ModelItem[]>([])
    const [loading, setLoading] = React.useState(false)
    const [converting, setConverting] = React.useState<string | null>(null) // Path of model being converted
    const [quantization, setQuantization] = React.useState<string>("4bit")

    const fetchModels = async () => {
        setLoading(true)
        try {
            const res = await fetch("http://localhost:8000/api/models/local")
            if (res.ok) {
                const data = await res.json()
                setModels(data)
            }
        } catch (e) {
            console.error("Failed to fetch models", e)
        } finally {
            setLoading(false)
        }
    }

    React.useEffect(() => {
        fetchModels()
    }, [])

    const handleConvert = async (modelPath: string) => {
        setConverting(modelPath)
        try {
            const res = await fetch("http://localhost:8000/api/models/convert", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    model_path_name: modelPath,
                    quantization: quantization
                })
            })
            if (res.ok) {
                // Determine success, maybe trigger a toast or re-fetch locally
                // Ideally backend would push status via WS, but for now we rely on user checking logs or refreshing later
                alert(`Conversion started with ${quantization}! Check system logs for progress.`)
            } else {
                alert("Failed to start conversion.")
            }
        } catch (e) {
            console.error("Conversion request failed", e)
        } finally {
            setConverting(null)
            // Re-fetch after a short delay or let user do it
            setTimeout(fetchModels, 2000)
        }
    }

    return (
        <Card className="border-white/10 bg-black/20 backdrop-blur-sm">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <HardDrive className="w-5 h-5 text-purple-500" />
                            Local Models
                        </CardTitle>
                        <CardDescription>Manage and convert HuggingFace models to MLX</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" size="sm" className="gap-2">
                                    {quantization} <ChevronDown className="w-4 h-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Quantization</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => setQuantization("4bit")}>
                                    4-bit (Recommended)
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => setQuantization("8bit")}>
                                    8-bit
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => setQuantization("fp16")}>
                                    Float16 (Original)
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => setQuantization("bf16")}>
                                    Bfloat16
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                        <Button variant="outline" size="sm" onClick={fetchModels} disabled={loading}>
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Refresh"}
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {models.length === 0 && !loading && (
                        <div className="text-center text-muted-foreground py-8">
                            No models found in <code>backend/models</code>
                        </div>
                    )}

                    {models.map((model) => (
                        <div key={model.path} className="flex items-center justify-between p-4 rounded-lg border bg-background/50 hover:bg-background/80 transition-colors">
                            <div className="space-y-1">
                                <div className="font-medium flex items-center gap-2">
                                    {model.id}
                                    {model.is_mlx && <Badge variant="secondary" className="text-xs">MLX Native</Badge>}
                                    {!model.is_mlx && !model.has_mlx_converted && <Badge variant="outline" className="text-xs">HF Source</Badge>}
                                </div>
                                <div className="text-xs text-muted-foreground font-mono">{model.path}</div>
                            </div>

                            <div className="flex items-center gap-2">
                                {model.has_mlx_converted ? (
                                    <Badge className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-green-500/50">
                                        <Check className="w-3 h-3 mr-1" /> Converted
                                    </Badge>
                                ) : model.is_mlx ? (
                                    <Badge variant="secondary">Ready</Badge>
                                ) : (
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => handleConvert(model.path)}
                                        disabled={!!converting}
                                    >
                                        {converting === model.path ? (
                                            <>
                                                <Loader2 className="w-3 h-3 mr-2 animate-spin" /> Starting...
                                            </>
                                        ) : (
                                            <>
                                                Convert <ArrowRight className="w-3 h-3 ml-2" />
                                            </>
                                        )}
                                    </Button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}
