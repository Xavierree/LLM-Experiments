import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, RefreshCcw, Database, Tag, Star, Calendar } from "lucide-react"
import { cn } from "@/lib/utils"

interface MemoryItem {
    text: string
    type: string
    importance: number
    timestamp: number
}

const TYPE_COLORS: Record<string, string> = {
    profile: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    preference: "bg-pink-500/10 text-pink-500 border-pink-500/20",
    pet: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    possession: "bg-green-500/10 text-green-500 border-green-500/20",
    state: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    other: "bg-slate-500/10 text-slate-500 border-slate-500/20",
}

export function MemoryExplorer() {
    const [memories, setMemories] = React.useState<MemoryItem[]>([])
    const [isLoading, setIsLoading] = React.useState(true)

    const fetchMemories = async () => {
        setIsLoading(true)
        try {
            const res = await fetch("http://localhost:8000/api/memory")
            if (res.ok) {
                const data = await res.json()
                setMemories(data)
            }
        } catch (e) {
            console.error("Failed to fetch memories", e)
        } finally {
            setIsLoading(false)
        }
    }

    React.useEffect(() => {
        fetchMemories()
    }, [])

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2">
                        <Database className="w-5 h-5 text-indigo-500" />
                        Memory Storage
                    </CardTitle>
                    <CardDescription>
                        Long-term facts and user preferences stored in the semantic vector database.
                    </CardDescription>
                </div>
                <Button variant="outline" size="icon" onClick={fetchMemories} disabled={isLoading}>
                    <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                </Button>
            </CardHeader>
            <CardContent>
                {isLoading && memories.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                        <Loader2 className="w-8 h-8 animate-spin mb-2" />
                        <p>Loading neural pathways...</p>
                    </div>
                ) : memories.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
                        <Database className="w-12 h-12 mx-auto mb-3 opacity-20" />
                        <p>No long-term memories formed yet.</p>
                        <p className="text-xs mt-1">Chat with the AI to build its knowledge base.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
                        {memories.map((mem, i) => (
                            <div key={i} className="p-4 rounded-lg bg-muted/40 border border-border hover:bg-muted/60 transition-colors space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium capitalize", TYPE_COLORS[mem.type] || TYPE_COLORS.other)}>
                                        {mem.type}
                                    </span>
                                    <div className="flex items-center text-xs text-muted-foreground gap-3">
                                        <span className="flex items-center gap-1">
                                            <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                                            {mem.importance}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3 h-3" />
                                            {new Date(mem.timestamp * 1000).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>
                                <p className="text-sm font-medium leading-relaxed">
                                    "{mem.text}"
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
