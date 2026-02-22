"use client"

import * as React from "react"
import { ModeSelector } from "@/components/features/ModeSelector"
import { PromptInput } from "@/components/features/PromptInput"
import { RagDialog } from "@/components/features/RagDialog"
import { ResponseActions } from "@/components/features/ResponseActions"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { ChatArea } from "@/components/layout/ChatArea"
import { Button } from "@/components/ui/button"
import { MODELS_BY_MODE } from "@/lib/constants"

interface Message {
  role: "user" | "assistant"
  content: string
  steps?: any[]
  isReasoning?: boolean
  mode?: string
  sources?: any[]
  isPending?: boolean
  turnId?: string
  iterations?: any[]
}

export default function InferencePage() {
  const [mode, setMode] = React.useState("chat")
  const [selectedModel, setSelectedModel] = React.useState("qwen") // Default to qwen
  const [input, setInput] = React.useState("")
  const [messages, setMessages] = React.useState<Message[]>([])
  const [loading, setLoading] = React.useState(false)
  const [sessions, setSessions] = React.useState<any[]>([])
  const [currentSessionId, setCurrentSessionId] = React.useState<string | null>(null)

  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false)
  const [ragOpen, setRagOpen] = React.useState(false)
  const [forceSearch, setForceSearch] = React.useState(false)

  // Refinement state
  const [pendingTurn, setPendingTurn] = React.useState<any | null>(null)
  const [isRefining, setIsRefining] = React.useState(false)

  // Generation Params
  const [temperature, setTemperature] = React.useState(0.7)
  const [maxTokens, setMaxTokens] = React.useState(8192)

  // -- Session Logic --
  React.useEffect(() => { fetchSessions() }, [])

  const fetchSessions = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/sessions")
      if (res.ok) setSessions(await res.json())
    } catch (e) { console.error(e) }
  }

  const createSession = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Chat" })
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentSessionId(data.id)
        setMessages([])
        fetchSessions()
      }
    } catch (e) { console.error(e) }
  }

  const loadSession = async (id: string) => {
    try {
      setLoading(true)
      const res = await fetch(`http://localhost:8000/api/sessions/${id}`)
      if (res.ok) {
        const data = await res.json()
        setCurrentSessionId(data.id)

        // Handle Turns if messages are empty (New Refinement Logic)
        let msgs = data.messages || []
        if (data.turns && data.turns.length > 0) {
          msgs = []
          for (const t of data.turns) {
            msgs.push({ role: "user", content: t.prompt, mode: t.mode })

            // Determine assistant response
            let resp = t.final_output
            if (!resp && t.iterations && t.iterations.length > 0) {
              resp = t.iterations[t.iterations.length - 1].response
            }

            msgs.push({
              role: "assistant",
              content: resp || "",
              turnId: t.id,
              iterations: t.iterations,
              mode: t.mode,
              sources: (t.iterations && t.iterations.length > 0) ? t.iterations[t.iterations.length - 1].sources : []
              // If it's the last turn and not accepted, it might be pending?
              // For now, load as history.
            })
          }
        }
        setMessages(msgs)
      }
      setLoading(false)
    } catch (e) {
      console.error(e)
      setLoading(false)
    }
  }

  const togglePin = async (e: React.MouseEvent, sessionId: string, currentPinned: boolean) => {
    e.stopPropagation()
    try {
      await fetch(`http://localhost:8000/api/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pinned: !currentPinned })
      })
      fetchSessions()
    } catch (e) { console.error(e) }
  }

  // -- Refinement Logic --
  const handleAccept = async () => {
    if (!pendingTurn || !currentSessionId) return

    try {
      await fetch("http://localhost:8000/api/chat/turn/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId })
      })

      // Move pending message to permanent history
      setMessages(prev => prev.map(msg =>
        msg.turnId === pendingTurn.id
          ? { ...msg, isPending: false }
          : msg
      ))

      setPendingTurn(null)
      fetchSessions()
    } catch (e) {
      console.error("Failed to accept turn:", e)
    }
  }

  const handleReject = async (correction: any) => {
    // Check mode
    if (mode === 'agent') {
      const payload = correction // Object { planner, executor, synthesis }
      setIsRefining(true)
      try {
        const res = await fetch("http://localhost:8000/api/chat/agent/refine", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            corrections: payload
          })
        })
        if (res.ok) {
          const newState = await res.json()
          // Update the LAST message with new content
          setMessages(prev => {
            const newHist = [...prev]
            const lastMsg = newHist[newHist.length - 1]
            lastMsg.content = newState.final_output
            // We might want to update steps visualization too if we had it stored
            return newHist
          })
        }
      } catch (e) { console.error(e) }
      finally { setIsRefining(false) }
      return
    }

    if (!pendingTurn || !currentSessionId) return

    setIsRefining(true)
    try {
      const res = await fetch("http://localhost:8000/api/chat/turn/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          correction: correction,
          temperature: temperature,
          max_tokens: maxTokens
        })
      })

      if (res.ok) {
        const updatedTurn = await res.json()
        setPendingTurn(updatedTurn)

        // Update the pending message with the new response
        const latestResponse = updatedTurn.iterations[updatedTurn.iterations.length - 1].response
        setMessages(prev => prev.map(msg =>
          msg.turnId === updatedTurn.id
            ? { ...msg, content: latestResponse, iterations: updatedTurn.iterations }
            : msg
        ))
      }
    } catch (e) {
      console.error("Failed to refine turn:", e)
    } finally {
      setIsRefining(false)
    }
  }

  // -- Chat Logic --
  const handleSubmit = async () => {
    if (!input.trim() || loading) return

    let activeSessionId = currentSessionId
    if (!activeSessionId) {
      // Create implicit session
      try {
        const res = await fetch("http://localhost:8000/api/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: input.slice(0, 30) })
        })
        if (res.ok) {
          const data = await res.json()
          activeSessionId = data.id
          setCurrentSessionId(data.id)
          fetchSessions()
        }
      } catch (e) { console.error(e) }
    }

    const userMsg: Message = { role: "user", content: input, mode }
    setMessages(prev => [...prev, userMsg])
    const currentInput = input
    setInput("")
    setLoading(true)

    // Use refinement API for chat/general modes
    if (mode !== "reasoning" && mode !== "agent") {
      try {
        const res = await fetch("http://localhost:8000/api/chat/turn/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: activeSessionId,
            prompt: currentInput,
            model: selectedModel,
            mode: mode,
            temperature: temperature,
            max_tokens: maxTokens,
            force_search: forceSearch
          })
        })

        if (res.ok) {
          const turn = await res.json()
          setPendingTurn(turn)

          // Add assistant message with pending flag
          const initialResponse = turn.iterations[0].response

          // 1. Init empty to trigger typewriter mount
          const newMsgId = turn.id
          setMessages(prev => [...prev, {
            role: "assistant",
            content: "",
            isPending: true,
            turnId: newMsgId,
            iterations: turn.iterations,
            mode
          }])

          // 2. Hydrate content to trigger typewriter effect
          setTimeout(() => {
            setMessages(prev => prev.map(m =>
              m.turnId === newMsgId
                ? { ...m, content: initialResponse, sources: turn.iterations[0].sources }
                : m
            ))
          }, 10)
        }
      } catch (e) {
        console.error("Failed to start turn:", e)
        setMessages(prev => {
          const newHistory = [...prev]
          newHistory.push({
            role: "assistant",
            content: "**Error:** Failed to generate response."
          })
          return newHistory
        })
      } finally {
        setLoading(false)
      }
      return
    }

    // Keep WebSocket for reasoning/agent mode
    setMessages(prev => [...prev, { role: "assistant", content: "", isReasoning: mode === "reasoning" || mode === "agent", steps: [], mode }])

    try {
      const socket = new WebSocket("ws://localhost:8000/api/ws/chat")
      socket.onopen = () => {
        socket.send(JSON.stringify({
          message: currentInput,
          mode: mode,
          model: selectedModel, // Send selected model
          temperature: temperature,
          maxTokens: maxTokens,
          sessionId: activeSessionId,
          forceSearch: forceSearch,
          useRag: true // Always true per previous fix
        }))
      }

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setMessages(prev => {
          const newHistory = [...prev]
          const lastIndex = newHistory.length - 1
          const lastMsg = { ...newHistory[lastIndex] }
          newHistory[lastIndex] = lastMsg

          if (lastMsg.role !== "assistant") return prev

          if (data.type === "plan") {
            const currentSteps = lastMsg.steps || []
            lastMsg.steps = [...currentSteps, { type: "plan", content: data.content }]
          } else if (data.type === "step") {
            const currentSteps = lastMsg.steps || []
            lastMsg.steps = [...currentSteps, { type: "step", index: data.index, step: data.step, result: data.result }]
          } else if (data.type === "final") {
            lastMsg.content = data.content
            lastMsg.sources = data.sources

            // Enable Refinement Actions
            lastMsg.isPending = true
            const agentTurnId = `agent-${Date.now()}`
            lastMsg.turnId = agentTurnId
            setPendingTurn({ id: agentTurnId })

            socket.close()
            setLoading(false)
            fetchSessions()
          }
          return newHistory
        })
      }

      socket.onerror = (error) => {
        console.error("WebSocket Error:", error)
        setMessages(prev => {
          const newHistory = [...prev]
          const lastMsg = newHistory[newHistory.length - 1]
          lastMsg.content = "**Error:** Connection failed."
          return newHistory
        })
        setLoading(false)
      }
    } catch (e) {
      console.error(e)
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans">
      {/* Sidebar */}
      <AppSidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onLoadSession={loadSession}
        onCreateSession={createSession}
        onTogglePin={togglePin}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full relative">

        {/* Top Bar (Minimal) */}
        <div className="absolute top-0 left-0 right-0 z-10 p-4 flex justify-between items-center pointer-events-none">
          <div className="pointer-events-auto">
            {/* Reserved for Future Top Controls */}
          </div>
        </div>

        {/* Chat Area */}
        <ChatArea
          messages={messages}
          loading={loading}
          onUploadClick={() => setRagOpen(true)}
          onReasoningClick={() => {
            setMode("reasoning")
            setSelectedModel("auto") // Ensure correct model for reasoning
          }}
          onAcceptResponse={handleAccept}
          onRejectResponse={handleReject}
          isRefining={isRefining}
        />

        {/* Input Area (Bottom) */}
        <div className="w-full p-4 pb-6 bg-gradient-to-t from-background via-background to-transparent z-10">
          <div className="max-w-3xl mx-auto">
            <PromptInput
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              isLoading={loading}
              forceSearch={forceSearch}
              setForceSearch={setForceSearch}
              onTriggerUpload={() => setRagOpen(true)}
              currentMode={mode}
              onModeChange={(newMode) => {
                setMode(newMode)
                // Auto-select first model for the mode
                if (newMode === 'reasoning') {
                  setSelectedModel('auto')
                } else {
                  const firstModel = MODELS_BY_MODE[newMode]?.[0]?.id
                  if (firstModel) setSelectedModel(firstModel)
                }
              }}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              temperature={temperature}
              onTemperatureChange={setTemperature}
              maxTokens={maxTokens}
              onMaxTokensChange={setMaxTokens}
            />
          </div>
        </div>
      </div>

      {/* Dialogs */}
      <RagDialog open={ragOpen} onOpenChange={setRagOpen} />

    </div>
  )
}
