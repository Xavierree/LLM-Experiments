"use client"

import * as React from "react"
import { Check, Copy } from "lucide-react"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface CodeBlockProps {
    language: string
    value: string
}

export function CodeBlock({ language, value }: CodeBlockProps) {
    const [isCopied, setIsCopied] = React.useState(false)

    const copyToClipboard = async () => {
        if (!value) return
        await navigator.clipboard.writeText(value)
        setIsCopied(true)
        setTimeout(() => setIsCopied(false), 2000)
    }

    return (
        <div className="relative w-full rounded-lg overflow-hidden border border-white/10 bg-[#1e1e1e] my-4 group shadow-lg">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] border-b border-white/5">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground uppercase">
                        {language || "text"}
                    </span>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-white/10"
                    onClick={copyToClipboard}
                    title="Copy code"
                >
                    {isCopied ? (
                        <Check className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                        <Copy className="w-3.5 h-3.5" />
                    )}
                </Button>
            </div>

            {/* Code Body */}
            <div className="relative">
                <SyntaxHighlighter
                    language={language || "text"}
                    style={vscDarkPlus}
                    customStyle={{
                        margin: 0,
                        padding: "1rem",
                        background: "transparent",
                        fontSize: "0.875rem",
                        lineHeight: "1.5",
                    }}
                    showLineNumbers={true}
                    lineNumberStyle={{
                        minWidth: "2em",
                        paddingRight: "1em",
                        color: "#6e6e6e",
                        textAlign: "right"
                    }}
                    wrapLines={true}
                >
                    {value}
                </SyntaxHighlighter>
            </div>
        </div>
    )
}
