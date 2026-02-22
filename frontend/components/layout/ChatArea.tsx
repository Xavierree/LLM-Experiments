"use client"

import * as React from "react"
import { Bot, User, Sparkles, Zap, BrainCircuit, FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import { StreamingOutput } from "@/components/features/StreamingOutput"
import { ResponseActions } from "@/components/features/ResponseActions"

interface Message {
    role: "user" | "assistant"
    content: string
    steps?: any[]
    isReasoning?: boolean
    mode?: string
    sources?: string[]
    isPending?: boolean
    turnId?: string
    iterations?: any[]
}

interface ChatAreaProps {
    messages: Message[]
    loading: boolean
    onUploadClick?: () => void
    onReasoningClick?: () => void
    onAcceptResponse?: () => void
    onRejectResponse?: (correction: string) => void
    isRefining?: boolean
}

export function ChatArea({ messages, loading, onUploadClick, onReasoningClick, onAcceptResponse, onRejectResponse, isRefining }: ChatAreaProps) {
    const scrollRef = React.useRef<HTMLDivElement>(null)

    React.useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages, loading])

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500">
                <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 p-6 rounded-3xl mb-6 shadow-2xl backdrop-blur-sm border border-white/5">
                    <BrainCircuit className="w-16 h-16 text-indigo-400" />
                </div>
                <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-white/50 bg-clip-text text-transparent mb-3">
                    How can I help you today?
                </h2>
                <p className="text-muted-foreground max-w-md text-lg">
                    I can help you reason through problems, analyze uploaded documents, or just chat.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-12 w-full max-w-2xl">
                    <div
                        onClick={onUploadClick}
                        className="p-4 bg-secondary/30 border border-white/5 rounded-xl text-left hover:bg-secondary/50 transition-colors cursor-pointer group"
                    >
                        <Zap className="w-5 h-5 text-yellow-400 mb-2 group-hover:scale-110 transition-transform" />
                        <h3 className="font-semibold text-sm mb-1">Analyze Documentation</h3>
                        <p className="text-xs text-muted-foreground">Upload a PDF and ask questions about it.</p>
                    </div>
                    <div
                        onClick={onReasoningClick}
                        className="p-4 bg-secondary/30 border border-white/5 rounded-xl text-left hover:bg-secondary/50 transition-colors cursor-pointer group"
                    >
                        <Sparkles className="w-5 h-5 text-purple-400 mb-2 group-hover:scale-110 transition-transform" />
                        <h3 className="font-semibold text-sm mb-1">Reasoning Task</h3>
                        <p className="text-xs text-muted-foreground">Solve a complex logic puzzle step-by-step.</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-0 py-6 pb-32 scrollbar-thin">
            <div className="max-w-3xl mx-auto space-y-8">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={cn(
                            "flex gap-4 group",
                            msg.role === "user" ? "justify-end" : "justify-start"
                        )}
                    >
                        {msg.role === "assistant" && (
                            <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 mt-1">
                                <Bot className="w-4 h-4 text-indigo-400" />
                            </div>
                        )}

                        <div className={cn(
                            "relative max-w-[85%] rounded-2xl p-5 shadow-sm",
                            msg.role === "user"
                                ? "bg-secondary text-secondary-foreground"
                                : "bg-transparent text-foreground px-0 py-0 shadow-none border-none max-w-[100%]" // AI messages blend in
                        )}>
                            {msg.role === "assistant" ? (
                                <>
                                    <StreamingOutput
                                        content={msg.content}
                                        isReasoning={msg.isReasoning}
                                        reasoningSteps={msg.steps}
                                        sources={msg.sources}
                                    />
                                    {msg.isPending && onAcceptResponse && onRejectResponse && (
                                        <ResponseActions
                                            onAccept={onAcceptResponse}
                                            onReject={onRejectResponse}
                                            isProcessing={isRefining || false}
                                            mode={msg.mode}
                                        />
                                    )}
                                </>
                            ) : (
                                <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                            )}

                            {/* Sources Chip for AI responses if any */}
                            {/* This is handled inside StreamingOutput usually, but we could enforce it here too */}
                        </div>

                        {msg.role === "user" && (
                            <div className="w-8 h-8 rounded-full bg-secondary border border-white/10 flex items-center justify-center shrink-0 mt-1">
                                <User className="w-4 h-4 text-muted-foreground" />
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="flex gap-4 justify-start animate-pulse">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                            <Bot className="w-4 h-4 text-indigo-400" />
                        </div>
                        <div className="space-y-2 mt-2">
                            <div className="h-4 w-4 bg-muted/50 rounded-full animate-bounce delay-0 inline-block mr-1"></div>
                            <div className="h-4 w-4 bg-muted/50 rounded-full animate-bounce delay-150 inline-block mr-1"></div>
                            <div className="h-4 w-4 bg-muted/50 rounded-full animate-bounce delay-300 inline-block"></div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
