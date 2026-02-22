import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function GenerationControls() {
    return <Card><CardHeader><CardTitle>Generation Controls</CardTitle></CardHeader><CardContent>Params...</CardContent></Card>
}

export function AdapterSelector() {
    return <Card><CardHeader><CardTitle>Adapter Selector</CardTitle></CardHeader><CardContent>LoRA selection...</CardContent></Card>
}

export function PromptReplay() {
    return <Card><CardHeader><CardTitle>Prompt Replay</CardTitle></CardHeader><CardContent>History debug...</CardContent></Card>
}

export function FilterInspector() {
    return <Card><CardHeader><CardTitle>Filter Inspector</CardTitle></CardHeader><CardContent>Safety filters...</CardContent></Card>
}
