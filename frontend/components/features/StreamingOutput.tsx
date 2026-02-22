"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover"
import { Globe } from "lucide-react"
import { CodeBlock } from "@/components/ui/code-block"

interface StreamingOutputProps {
    content: string
    isReasoning?: boolean
    reasoningSteps?: any[]
    sources?: any[]
}

export function StreamingOutput({ content, isReasoning, reasoningSteps, sources }: StreamingOutputProps) {
    const [displayedContent, setDisplayedContent] = React.useState(content || "")
    const bottomRef = React.useRef<HTMLDivElement>(null)

    // Typewriter effect
    React.useEffect(() => {
        // If content is same or empty, sync and return
        if (!content) {
            if (displayedContent !== "") setDisplayedContent("")
            return
        }

        if (content === displayedContent) return

        // If content shrank (edit/correction?), snap immediately
        if (content.length < displayedContent.length) {
            setDisplayedContent(content)
            return
        }

        const diff = content.length - displayedContent.length

        // Dynamic speed/chunking
        // if diff is huge, we want to finish in ~1s max
        // e.g. 500 chars -> 2ms/char or chunk 5 chars every 10ms
        const timeToFinish = 1000 // ms target
        const intervalTime = 10
        const steps = timeToFinish / intervalTime // 100 steps
        const chunk = Math.ceil(diff / steps) // at least 1

        const interval = setInterval(() => {
            setDisplayedContent(prev => {
                if (prev.length >= content.length) {
                    clearInterval(interval)
                    return content
                }
                return content.slice(0, prev.length + chunk)
            })
        }, intervalTime)

        return () => clearInterval(interval)
    }, [content])

    React.useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [displayedContent, reasoningSteps])

    return (
        <div className="space-y-4">
            {/* Reasoning Timeline (Only if reasoning mode) */}
            {isReasoning && reasoningSteps && reasoningSteps.length > 0 && (
                <div className="space-y-4 mb-8">
                    {reasoningSteps.map((step, idx) => (
                        <div key={idx} className="border-l-2 border-primary/20 pl-4 py-2 relative">
                            <div className="absolute -left-[9px] top-6 w-4 h-4 rounded-full bg-background border-2 border-primary" />
                            <div className="text-xs uppercase font-bold text-muted-foreground mb-1">
                                {step.type === "plan" ? "🧠 Planning" : `🔧 Step ${step.index + 1}`}
                            </div>

                            {step.type === "plan" ? (
                                <div className="bg-muted/50 p-3 rounded-md text-sm font-mono">
                                    <div className="font-semibold text-primary mb-2">{step.content.objective}</div>
                                    <ul className="list-disc list-inside space-y-1">
                                        {step.content.steps.map((s: string, i: number) => (
                                            <li key={i}>{s}</li>
                                        ))}
                                    </ul>
                                </div>
                            ) : (
                                <div className="text-sm">
                                    <div className="font-medium mb-1">{step.step}</div>
                                    <pre className="bg-black/10 p-2 rounded text-xs overflow-x-auto">
                                        {step.result}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Final Output */}
            {displayedContent && (
                <div className={cn("prose prose-invert max-w-none text-zinc-100", isReasoning && "border-t pt-4 mt-4")}>
                    {isReasoning && <h3 className="text-lg font-bold flex items-center gap-2 mb-4 text-purple-400">🎓 Final Answer</h3>}

                    {/* Custom Parsing for <think> tags */}
                    {(() => {
                        const parts = displayedContent.split(/(<think>[\s\S]*?<\/think>)/g);
                        return parts.map((part, index) => {
                            if (part.startsWith("<think>")) {
                                const thinkContent = part.replace(/<\/?think>/g, "").trim();
                                return (
                                    <div key={index} className="my-4 border-l-4 border-amber-500/50 bg-amber-500/10 p-4 rounded-r-lg">
                                        <div className="text-xs font-bold text-amber-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                            💭 Thought Process
                                        </div>
                                        <div className="text-sm text-zinc-400 italic leading-relaxed whitespace-pre-wrap">
                                            {thinkContent}
                                        </div>
                                    </div>
                                );
                            }

                            if (!part.trim()) return null;

                            return (
                                <ReactMarkdown
                                    key={index}
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        // Headings
                                        h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-4 text-white pb-2 border-b border-white/10" {...props} />,
                                        h2: ({ node, ...props }) => <h2 className="text-xl font-semibold mt-6 mb-3 text-white flex items-center gap-2" {...props} />,
                                        h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-indigo-200" {...props} />,

                                        // Text
                                        p: ({ node, ...props }) => <p className="leading-7 mb-4 text-zinc-300" {...props} />,
                                        strong: ({ node, ...props }) => <strong className="font-bold text-white" {...props} />,
                                        em: ({ node, ...props }) => <em className="italic text-zinc-400" {...props} />,

                                        // Lists
                                        ul: ({ node, ...props }) => <ul className="my-4 ml-6 list-disc [&>li]:mt-2 text-zinc-300 marker:text-zinc-500" {...props} />,
                                        ol: ({ node, ...props }) => <ol className="my-4 ml-6 list-decimal [&>li]:mt-2 text-zinc-300 marker:text-zinc-500" {...props} />,
                                        li: ({ node, ...props }) => <li className="leading-7" {...props} />,

                                        // Blockquotes
                                        blockquote: ({ node, ...props }) => (
                                            <blockquote className="border-l-4 border-indigo-500/50 pl-4 py-1 my-4 italic text-zinc-400 bg-white/5 rounded-r" {...props} />
                                        ),

                                        // Tables
                                        table: ({ node, ...props }) => (
                                            <div className="my-6 w-full overflow-y-auto rounded-lg border border-white/10">
                                                <table className="w-full" {...props} />
                                            </div>
                                        ),
                                        thead: ({ node, ...props }) => <thead className="bg-white/5 text-left" {...props} />,
                                        tr: ({ node, ...props }) => <tr className="border-b border-white/5 even:bg-white/5 transition-colors hover:bg-white/10" {...props} />,
                                        th: ({ node, ...props }) => <th className="border-b border-white/10 px-4 py-2 text-left font-bold text-white" {...props} />,
                                        td: ({ node, ...props }) => <td className="px-4 py-2 text-sm text-zinc-300" {...props} />,

                                        // Code Blocks & Inline Code
                                        code: ({ node, inline, className, children, ...props }: any) => {
                                            const match = /language-(\w+)/.exec(className || "")
                                            const lang = match ? match[1] : ""
                                            const value = String(children).replace(/\n$/, "")

                                            const isMultiLine = value.includes('\n')

                                            if (!inline && isMultiLine) {
                                                return <CodeBlock language={lang || "text"} value={value} />
                                            }

                                            return (
                                                <code className="bg-white/10 text-rose-300 px-1.5 py-0.5 rounded text-sm font-mono border border-white/5" {...props}>
                                                    {children}
                                                </code>
                                            )
                                        }
                                    }}
                                >
                                    {part}
                                </ReactMarkdown>
                            );
                        });
                    })()}
                </div>
            )}

            {/* Sources Button */}
            {sources && sources.length > 0 && (
                <div className="pt-2 border-t mt-4">
                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="outline" size="sm" className="gap-2 rounded-full h-8 text-xs">
                                <Globe className="w-3.5 h-3.5" />
                                Sources
                                <span className="bg-muted-foreground/20 px-1.5 py-0.5 rounded text-[10px] ml-1">
                                    {sources.length}
                                </span>
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-80 p-0 bg-neutral-950 border-neutral-800 shadow-xl" side="right" align="start">
                            <div className="bg-neutral-900/50 p-3 border-b border-neutral-800 text-sm font-medium text-neutral-100">
                                Web Sources
                            </div>
                            <div className="max-h-[300px] overflow-y-auto p-2 space-y-1">
                                {sources.map((src, i) => (
                                    <a
                                        key={i}
                                        href={src.link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block p-2 hover:bg-neutral-900 rounded-md text-sm group transition-colors"
                                    >
                                        <div className="font-medium text-neutral-200 group-hover:underline truncate">
                                            {src.title}
                                        </div>
                                        <div className="text-xs text-neutral-400 line-clamp-2 mt-1">
                                            {src.snippet}
                                        </div>
                                        <div className="text-[10px] text-neutral-500 mt-1 truncate font-mono">
                                            {new URL(src.link).hostname}
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </PopoverContent>
                    </Popover>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    )
}
