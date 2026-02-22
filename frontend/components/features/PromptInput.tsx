"use client"

import * as React from "react"
import TextareaAutosize from "react-textarea-autosize"
import { Button } from "@/components/ui/button"
import { ModeSelector } from "@/components/features/ModeSelector"
import { SendHorizontal, Globe, Paperclip } from "lucide-react"
import { cn } from "@/lib/utils"

interface PromptInputProps {
    value: string
    onChange: (val: string) => void
    onSubmit: () => void
    isLoading: boolean
    forceSearch: boolean
    setForceSearch: (val: boolean) => void
    onTriggerUpload: () => void
    currentMode: string
    onModeChange: (mode: string) => void
    selectedModel?: string
    onModelChange?: (model: string) => void
    temperature?: number
    onTemperatureChange?: (temp: number) => void
    maxTokens?: number
    onMaxTokensChange?: (tokens: number) => void
}

export function PromptInput({
    value,
    onChange,
    onSubmit,
    isLoading,
    forceSearch,
    setForceSearch,
    onTriggerUpload,
    currentMode,
    onModeChange,
    selectedModel,
    onModelChange: onModelChangeProp,
    temperature,
    onTemperatureChange,
    maxTokens,
    onMaxTokensChange
}: PromptInputProps) {

    const textareaRef = React.useRef<HTMLTextAreaElement>(null)

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            onSubmit()
        }
    }

    const handleMaxTokensSubmit = () => {
        textareaRef.current?.focus()
    }

    return (
        <div className="w-full max-w-3xl mx-auto relative group">

            {/* Mode Selectors (Floating attached to top) */}
            <div className="absolute -top-12 left-0 pl-1 p-1 bg-background/80 backdrop-blur-md border border-white/10 rounded-full shadow-lg z-20">
                <ModeSelector
                    currentMode={currentMode}
                    onModeChange={onModeChange}
                    selectedModel={selectedModel}
                    onModelChange={onModelChangeProp}
                    temperature={temperature}
                    onTemperatureChange={onTemperatureChange}
                    maxTokens={maxTokens}
                    onMaxTokensChange={onMaxTokensChange}
                    onMaxTokensSubmit={handleMaxTokensSubmit}
                />
            </div>

            <div className="relative flex items-end w-full p-3 bg-secondary/40 backdrop-blur-md border border-white/10 rounded-2xl shadow-sm focus-within:ring-1 focus-within:ring-white/20 transition-all">

                {/* Left Actions */}
                <div className="flex items-center gap-1 pb-1 pr-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-white/10"
                        onClick={onTriggerUpload}
                        title="Upload File"
                    >
                        <Paperclip className="h-5 w-5" />
                    </Button>

                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                            "h-8 w-8 rounded-full transition-colors",
                            forceSearch
                                ? "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30"
                                : "text-muted-foreground hover:text-foreground hover:bg-white/10"
                        )}
                        onClick={() => setForceSearch(!forceSearch)}
                        title="Search Web"
                    >
                        <Globe className="h-5 w-5" />
                    </Button>
                </div>

                {/* Text Area */}
                <TextareaAutosize
                    ref={textareaRef}
                    minRows={1}
                    maxRows={8}
                    className="flex-1 max-h-[200px] bg-transparent border-none resize-none focus:ring-0 px-2 py-2 text-sm md:text-base leading-relaxed scrollbar-hide placeholder:text-muted-foreground/50"
                    placeholder="Ask anything..."
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                />

                {/* Right Actions (Send) */}
                <div className="pb-1 pl-2">
                    <Button
                        size="icon"
                        onClick={onSubmit}
                        disabled={!value.trim() || isLoading}
                        className={cn(
                            "h-8 w-8 rounded-full transition-all duration-200",
                            value.trim() ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                        )}
                    >
                        <SendHorizontal className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            <div className="text-center mt-2">
                <p className="text-[10px] text-muted-foreground/60">
                    AI can make mistakes. Check important info.
                </p>
            </div>
        </div>
    )
}
