"use client"

import * as React from "react"
import { Monitor, BrainCircuit, MessageSquare, Plus, ChevronDown } from "lucide-react"
import { MODELS_BY_MODE } from "@/lib/constants"
import { cn } from "@/lib/utils"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

interface ModeSelectorProps {
    currentMode: string
    onModeChange: (mode: string) => void
    selectedModel?: string
    onModelChange?: (model: string) => void
    temperature?: number
    onTemperatureChange?: (temp: number) => void
    maxTokens?: number
    onMaxTokensChange?: (tokens: number) => void
    onMaxTokensSubmit?: () => void
}

export function ModeSelector({
    currentMode,
    onModeChange,
    selectedModel,
    onModelChange,
    temperature = 0.7,
    onTemperatureChange = () => { },
    maxTokens = 1024,
    onMaxTokensChange = () => { },
    onMaxTokensSubmit = () => { }
}: ModeSelectorProps) {
    const modes = [
        { id: "chat", label: "Chat", icon: MessageSquare, defaultModel: "chat" },
        { id: "general", label: "General", icon: Monitor, defaultModel: "general" },
        { id: "code", label: "Code", icon: Monitor, defaultModel: "code" },
        { id: "agent", label: "Agent", icon: BrainCircuit, defaultModel: "planner" }
    ]

    const activeMode = modes.find(m => m.id === currentMode) || modes[0]
    const Icon = activeMode.icon
    const maxTokensRef = React.useRef<HTMLInputElement>(null)

    // Define models available per mode
    // Imported from constants to share with parent
    const modelsByMode = MODELS_BY_MODE

    // Fallback if selected model not in list? Parent handle logic.
    const currentModelList = modelsByMode[currentMode] || []
    const activeModelLabel = currentModelList.find(m => m.id === selectedModel)?.label || "Select Model"
    const isModelSelectable = currentMode !== 'reasoning' && currentMode !== 'agent'

    return (
        <div className="flex items-center gap-2">

            {/* Mode Selector */}
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-2 rounded-full border border-transparent bg-secondary/50 hover:bg-secondary text-secondary-foreground font-medium px-3 text-xs"
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {activeMode.label}
                        <ChevronDown className="w-3 h-3 opacity-50" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-[150px] bg-stone-900 border-white/10 text-stone-200">
                    {modes.map((mode) => (
                        <DropdownMenuItem
                            key={mode.id}
                            onClick={() => onModeChange(mode.id)}
                            className="gap-2 focus:bg-white/10 cursor-pointer text-xs"
                        >
                            <mode.icon className="w-3.5 h-3.5" />
                            <span>{mode.label}</span>
                        </DropdownMenuItem>
                    ))}
                </DropdownMenuContent>
            </DropdownMenu>

            {/* Model Selector */}
            <DropdownMenu>
                <DropdownMenuTrigger asChild disabled={!isModelSelectable}>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-2 rounded-full border border-transparent hover:bg-white/5 text-muted-foreground font-normal px-3 text-xs disabled:opacity-50"
                    >
                        <span>{activeModelLabel}</span>
                        {isModelSelectable && <ChevronDown className="w-3 h-3 opacity-50" />}
                    </Button>
                </DropdownMenuTrigger>
                {isModelSelectable && (
                    <DropdownMenuContent align="start" className="w-[180px] bg-stone-900 border-white/10 text-stone-200">
                        {currentModelList.map((m) => (
                            <DropdownMenuItem
                                key={m.id}
                                onClick={() => onModelChange && onModelChange(m.id)}
                                className={cn("gap-2 focus:bg-white/10 cursor-pointer text-xs", selectedModel === m.id && "bg-white/5 text-white")}
                            >
                                <span>{m.label}</span>
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                )}
            </DropdownMenu>

            {/* Separator */}
            <div className="w-px h-4 bg-white/10 mx-1" />

            {/* Temperature Input */}
            <div className="flex items-center gap-1 bg-secondary/30 rounded-full px-2 h-8 border border-transparent hover:bg-secondary/50 transition-colors" title="Input between 0.1 - 0.98">
                <span className="text-secondary-foreground/70 text-[10px] font-medium uppercase tracking-wider">Temp</span>
                <input
                    type="number"
                    min={0}
                    max={2}
                    step={0.01}
                    value={temperature}
                    onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault()
                            maxTokensRef.current?.focus()
                            maxTokensRef.current?.select()
                        }
                    }}
                    className="w-12 bg-transparent border-none text-xs text-center focus:ring-0 p-0 text-white font-mono [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    style={{ MozAppearance: 'textfield', colorScheme: 'dark' }}
                />
            </div>

            {/* Max Tokens Input */}
            <div className="flex items-center gap-1 bg-secondary/30 rounded-full px-2 h-8 border border-transparent hover:bg-secondary/50 transition-colors" title="Input between 1000-32000">
                <span className="text-secondary-foreground/70 text-[10px] font-medium uppercase tracking-wider">Max</span>
                <input
                    ref={maxTokensRef}
                    type="number"
                    min={128}
                    max={33000}
                    step={1}
                    value={maxTokens}
                    onChange={(e) => onMaxTokensChange(parseInt(e.target.value))}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault()
                            onMaxTokensSubmit()
                        }
                    }}
                    onBlur={(e) => {
                        let val = parseInt(e.target.value);
                        if (isNaN(val)) val = 1024;
                        // Round to nearest 1024
                        val = Math.round(val / 1024) * 1024;
                        if (val < 1024) val = 1024; // Minimum 1024
                        if (val > 33000) val = 33000;
                        onMaxTokensChange(val);
                    }}
                    className="w-14 bg-transparent border-none text-xs text-center focus:ring-0 p-0 text-white font-mono [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    style={{ MozAppearance: 'textfield', colorScheme: 'dark' }}
                />
            </div>
        </div>
    )
}
