"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Upload, X, FileText, CheckCircle, AlertCircle, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface RagDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function RagDialog({ open, onOpenChange }: RagDialogProps) {
    const [uploading, setUploading] = React.useState(false)
    const [files, setFiles] = React.useState<string[]>([])
    const [message, setMessage] = React.useState<{ type: 'success' | 'error', text: string } | null>(null)
    const inputRef = React.useRef<HTMLInputElement>(null)

    const fetchFiles = React.useCallback(async () => {
        try {
            const res = await fetch("http://localhost:8000/api/rag/files")
            if (res.ok) {
                const data = await res.json()
                setFiles(data.files || [])
            }
        } catch (e) {
            console.error("Failed to fetch files", e)
        }
    }, [])

    React.useEffect(() => {
        if (open) fetchFiles()
    }, [open, fetchFiles])

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        setMessage(null)

        const formData = new FormData()
        formData.append('file', file)

        try {
            const res = await fetch("http://localhost:8000/api/ingest", {
                method: 'POST',
                body: formData,
            })

            const data = await res.json()

            if (!res.ok) {
                throw new Error(data.detail || 'Upload failed')
            }

            setMessage({ type: 'success', text: `Success: ${data.chunks_added} chunks added.` })

            if (inputRef.current) inputRef.current.value = ""
            fetchFiles()

            setTimeout(() => {
                setMessage(null)
            }, 3000)

        } catch (err: any) {
            setMessage({ type: 'error', text: err.message })
        } finally {
            setUploading(false)
        }
    }

    const handleDelete = async (filename: string) => {
        try {
            const res = await fetch(`http://localhost:8000/api/rag/files/${filename}`, {
                method: 'DELETE'
            })
            if (res.ok) {
                fetchFiles()
                setMessage({ type: 'success', text: `Deleted ${filename}` })
                setTimeout(() => setMessage(null), 3000)
            } else {
                setMessage({ type: 'error', text: "Delete failed" })
            }
        } catch (e: any) {
            setMessage({ type: 'error', text: e.message })
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md bg-stone-950 border-white/10 text-stone-50">
                <DialogHeader>
                    <DialogTitle>Knowledge Base</DialogTitle>
                    <DialogDescription className="text-stone-400">
                        Manage files for RAG context. Supported: PDF, DOCX, TXT.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-col gap-4 mt-2">
                    <div
                        className="flex flex-col items-center justify-center p-8 border border-dashed border-white/10 rounded-xl bg-white/5 hover:bg-white/10 transition-colors gap-2 cursor-pointer"
                        onClick={() => inputRef.current?.click()}
                    >
                        <div className="bg-white/5 p-3 rounded-full mb-2">
                            <Upload className="w-5 h-5 text-stone-400" />
                        </div>
                        <p className="text-sm font-medium text-stone-300">
                            {uploading ? "Uploading..." : "Click to upload"}
                        </p>
                        <input
                            ref={inputRef}
                            type="file"
                            className="hidden"
                            accept=".pdf,.docx,.txt"
                            onChange={handleUpload}
                        />
                    </div>

                    {/* File List */}
                    {files.length > 0 && (
                        <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">My Files</div>
                            {files.map(file => (
                                <div key={file} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5 text-sm group hover:border-white/10 transition-colors">
                                    <div className="flex items-center gap-3 overflow-hidden">
                                        <FileText className="w-4 h-4 text-blue-400 shrink-0" />
                                        <span className="truncate text-stone-300">{file}</span>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6 text-stone-500 hover:text-red-400 hover:bg-red-400/10 opacity-0 group-hover:opacity-100 transition-all"
                                        onClick={() => handleDelete(file)}
                                        title="Delete file"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}

                    {message && (
                        <div className={cn(
                            "p-3 rounded-md flex items-center gap-2 text-sm animate-in fade-in slide-in-from-bottom-2",
                            message.type === 'success' ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                        )}>
                            {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                            {message.text}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}
