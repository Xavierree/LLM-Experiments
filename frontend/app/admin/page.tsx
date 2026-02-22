"use client"

import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Brain, Database, Shield, ArrowLeft } from "lucide-react"
import Link from "next/link"

// Components
import { MemoryExplorer } from "@/components/features/admin/MemoryExplorer"
import { DatasetManager } from "@/components/features/admin/DatasetManager"
import { TrainingDashboard } from "@/components/features/admin/TrainingDashboard"
import { TrainingPanel } from "@/components/features/TrainingPanel" // Reuse existing
import { RefineryPanel } from "@/components/features/admin/RefineryPanel"
import { SystemMonitor } from "@/components/features/admin/SystemMonitor"
import { ModelConverter } from "@/components/features/admin/ModelConverter"
import { GenerationControls, AdapterSelector, PromptReplay, FilterInspector } from "@/components/features/admin/OpsComponents"

export default function AdminPage() {
    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Button variant="ghost" size="icon">
                                <ArrowLeft className="w-5 h-5" />
                            </Button>
                        </Link>
                        <div>
                            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
                                Admin Dashboard
                            </h1>
                            <p className="text-muted-foreground">System Monitoring & Training Controls</p>
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <Tabs defaultValue="training" className="space-y-6">
                    <TabsList className="grid w-full grid-cols-4 max-w-2xl mx-auto bg-secondary/50 p-1 rounded-xl">
                        <TabsTrigger value="memory" className="flex items-center gap-2 rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">
                            <Brain className="w-4 h-4" /> Memory
                        </TabsTrigger>
                        <TabsTrigger value="models" className="flex items-center gap-2 rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">
                            <Brain className="w-4 h-4" /> Models
                        </TabsTrigger>
                        <TabsTrigger value="training" className="flex items-center gap-2 rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">
                            <Database className="w-4 h-4" /> Training
                        </TabsTrigger>
                        <TabsTrigger value="ops" className="flex items-center gap-2 rounded-lg data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all">
                            <Shield className="w-4 h-4" /> Ops
                        </TabsTrigger>
                    </TabsList>

                    {/* Memory Tab */}
                    <TabsContent value="memory" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                            <CardContent className="p-6">
                                <MemoryExplorer />
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Models Tab */}
                    <TabsContent value="models" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="space-y-6">
                            <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                <CardHeader>
                                    <CardTitle>System Monitor</CardTitle>
                                    <CardDescription>Real-time resource usage</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <SystemMonitor />
                                </CardContent>
                            </Card>
                            <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                <CardHeader>
                                    <CardTitle>Model Converter</CardTitle>
                                    <CardDescription>Convert HuggingFace models to MLX</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <ModelConverter />
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>

                    {/* Training Tab */}
                    <TabsContent value="training" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                            <div className="xl:col-span-2 space-y-6">
                                <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                    <CardHeader><CardTitle>Refinement Pipeline</CardTitle></CardHeader>
                                    <CardContent><RefineryPanel /></CardContent>
                                </Card>
                                <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                    <CardHeader><CardTitle>Training Control</CardTitle></CardHeader>
                                    <CardContent><TrainingPanel /></CardContent>
                                </Card>
                                <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                    <CardHeader><CardTitle>Dataset Management</CardTitle></CardHeader>
                                    <CardContent><DatasetManager /></CardContent>
                                </Card>
                            </div>
                            <div className="xl:col-span-1">
                                <Card className="border-white/10 bg-black/20 backdrop-blur-xl h-full">
                                    <CardHeader><CardTitle>Training Metrics</CardTitle></CardHeader>
                                    <CardContent><TrainingDashboard /></CardContent>
                                </Card>
                            </div>
                        </div>
                    </TabsContent>

                    {/* Ops Tab */}
                    <TabsContent value="ops" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                <CardContent className="pt-6"><GenerationControls /></CardContent>
                            </Card>
                            <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                <CardContent className="pt-6"><AdapterSelector /></CardContent>
                            </Card>
                            <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                <CardContent className="pt-6"><FilterInspector /></CardContent>
                            </Card>
                            <div className="lg:col-span-3">
                                <Card className="border-white/10 bg-black/20 backdrop-blur-xl">
                                    <CardHeader><CardTitle>Prompt Replay</CardTitle></CardHeader>
                                    <CardContent><PromptReplay /></CardContent>
                                </Card>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    )
}
