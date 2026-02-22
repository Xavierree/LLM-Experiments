"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { History, Plus, Pin, Trash2, Settings, MessageSquare, ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

interface Session {
    id: string
    title: string
    preview: string
    pinned: boolean
    updated_at?: string
}

interface AppSidebarProps {
    sessions: Session[]
    currentSessionId: string | null
    onLoadSession: (id: string) => void
    onCreateSession: () => void
    onTogglePin: (e: React.MouseEvent, id: string, current: boolean) => void
    collapsed: boolean
    setCollapsed: (v: boolean) => void
}

export function AppSidebar({
    sessions,
    currentSessionId,
    onLoadSession,
    onCreateSession,
    onTogglePin,
    collapsed,
    setCollapsed
}: AppSidebarProps) {

    return (
        <div
            className={cn(
                "relative flex flex-col h-full bg-black/50 backdrop-blur-xl border-r border-white/5 transition-all duration-300",
                collapsed ? "w-[60px]" : "w-[280px]"
            )}
        >
            {/* Toggle Button */}
            <div className="absolute -right-3 top-6 z-20">
                <Button
                    variant="outline"
                    size="icon"
                    className="h-6 w-6 rounded-full border shadow-md bg-background hover:bg-muted"
                    onClick={() => setCollapsed(!collapsed)}
                >
                    {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
                </Button>
            </div>

            {/* Header / New Chat */}
            <div className="p-3 border-b border-white/5">
                <Button
                    onClick={onCreateSession}
                    className={cn(
                        "w-full justify-start gap-2 transition-all",
                        collapsed ? "px-2 justify-center" : ""
                    )}
                    variant="secondary"
                >
                    <Plus className="w-4 h-4" />
                    {!collapsed && <span>New Chat</span>}
                </Button>
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
                {!collapsed && <div className="text-xs font-medium text-muted-foreground px-2 py-2 mb-2">Recent</div>}

                <div className="space-y-1">
                    {sessions.map(s => (
                        <div
                            key={s.id}
                            onClick={() => onLoadSession(s.id)}
                            className={cn(
                                "group flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors text-sm",
                                currentSessionId === s.id
                                    ? "bg-accent/50 text-foreground"
                                    : "hover:bg-sidebar-accent/50 text-muted-foreground hover:text-foreground",
                                collapsed && "justify-center"
                            )}
                        >
                            {collapsed ? (
                                <MessageSquare className="w-4 h-4 shrink-0" />
                            ) : (
                                <>
                                    <MessageSquare className="w-4 h-4 shrink-0 opacity-50" />
                                    <div className="flex-1 min-w-0">
                                        <div className="truncate font-medium">{s.title || "Untitled Chat"}</div>
                                    </div>
                                    {s.pinned && <Pin className="w-3 h-3 rotate-45 text-primary fill-primary/20 shrink-0" />}
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={(e) => onTogglePin(e, s.id, s.pinned)}
                                        >
                                            <Pin className={cn("w-3 h-3", s.pinned ? "fill-foreground" : "")} />
                                        </Button>
                                    </div>
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-white/5 mt-auto">
                <Link href="/admin">
                    <Button variant="ghost" className={cn("w-full justify-start gap-2", collapsed && "justify-center px-0")}>
                        <Settings className="w-4 h-4" />
                        {!collapsed && <span>Settings</span>}
                    </Button>
                </Link>
            </div>
        </div>
    )
}
