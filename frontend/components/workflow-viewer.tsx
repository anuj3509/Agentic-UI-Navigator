"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Download, ExternalLink } from "lucide-react"
import { Card } from "@/components/ui/card"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface WorkflowViewerProps {
  appName: string
  taskName: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function WorkflowViewer({ appName, taskName }: WorkflowViewerProps) {
  const [markdown, setMarkdown] = useState<string>("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [basePath, setBasePath] = useState<string>("")

  useEffect(() => {
    fetchWorkflow()
  }, [appName, taskName])

  const fetchWorkflow = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `${API_URL}/api/workflow/${encodeURIComponent(appName)}/${encodeURIComponent(taskName)}`
      )
      
      if (!response.ok) {
        throw new Error("Failed to load workflow")
      }
      
      const data = await response.json()
      setMarkdown(data.content)
      
      // Set base path for images: dataset/appName/taskName/
      const taskNameSlug = taskName.toLowerCase().replace(/\s+/g, '_')
      setBasePath(`dataset/${appName.toLowerCase()}/${taskNameSlug}`)
      
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    const downloadUrl = `${API_URL}/api/download/workflow/${encodeURIComponent(appName)}/${encodeURIComponent(taskName)}`
    window.open(downloadUrl, "_blank")
  }

  if (loading) {
    return (
      <Card className="p-6 bg-zinc-900/50 border-zinc-800">
        <p className="text-zinc-400">Loading workflow...</p>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6 bg-zinc-900/50 border-zinc-800">
        <p className="text-red-400">Error: {error}</p>
      </Card>
    )
  }

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 overflow-hidden relative z-50">
      {/* Header with Download Button */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <h3 className="text-lg font-semibold text-white">Guide Generated</h3>
        <Button
          onClick={handleDownload}
          size="sm"
          className="bg-orange-500 hover:bg-orange-600 text-white pointer-events-auto cursor-pointer"
        >
          <Download className="w-4 h-4 mr-2" />
          Download
        </Button>
      </div>

      {/* Markdown Content */}
      <div className="p-6 max-h-[70vh] overflow-y-auto overflow-x-hidden pointer-events-auto">
        <div className="prose prose-invert prose-orange max-w-none select-text">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              img: ({ node, ...props }) => {
                // Construct full path: basePath + relative screenshot path
                const imagePath = `${basePath}/${props.src}`
                return (
                  <img
                    {...props}
                    className="rounded-lg border border-zinc-700 my-4 w-full"
                    src={`${API_URL}/api/files/${imagePath}`}
                    alt={props.alt || "Step screenshot"}
                    onError={(e) => {
                      console.error("Failed to load image:", imagePath)
                    }}
                  />
                )
              },
              h1: ({ node, ...props }) => (
                <h1 className="text-3xl font-bold text-white mb-4 select-text" {...props} />
              ),
              h2: ({ node, ...props }) => (
                <h2 className="text-2xl font-semibold text-white mt-8 mb-3 select-text" {...props} />
              ),
              h3: ({ node, ...props }) => (
                <h3 className="text-xl font-medium text-orange-400 mt-6 mb-2 select-text" {...props} />
              ),
              p: ({ node, ...props }) => (
                <p className="text-zinc-300 mb-4 leading-relaxed select-text" {...props} />
              ),
              hr: ({ node, ...props }) => (
                <hr className="border-zinc-700 my-6" {...props} />
              ),
              strong: ({ node, ...props }) => (
                <strong className="text-orange-300 font-semibold select-text" {...props} />
              ),
              em: ({ node, ...props }) => (
                <em className="text-zinc-400 text-sm select-text" {...props} />
              ),
              ul: ({ node, ...props }) => (
                <ul className="list-disc list-inside text-zinc-300 mb-4 space-y-1 select-text" {...props} />
              ),
            }}
          >
            {markdown}
          </ReactMarkdown>
        </div>
      </div>
    </Card>
  )
}

