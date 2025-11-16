"use client"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Brain, Link, Folder, ArrowRight, ArrowRightToLine, Loader2 } from 'lucide-react'
import { LiquidMetal, PulsingBorder } from "@paper-design/shaders-react"
import { motion } from "framer-motion"
import { useState, useEffect, useRef } from "react"
import { useToast } from "@/hooks/use-toast"
import { WorkflowViewer } from "./workflow-viewer"

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
  status?: "pending" | "success" | "error"
  metadata?: any
  showWorkflow?: boolean
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function ChatInterface() {
  const [isFocused, setIsFocused] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState("")
  const wsRef = useRef<WebSocket | null>(null)
  const { toast } = useToast()

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws`)
      
      ws.onopen = () => {
        console.log("WebSocket connected")
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === "status") {
          setStatusMessage(data.message)
        } else if (data.type === "complete") {
          setStatusMessage("")
          setIsLoading(false)
          
          // Update the last user message to add workflow viewer
          setMessages(prev => {
            // Remove any "Processing..." assistant message
            const filtered = prev.filter(msg => !(msg.role === "assistant" && msg.status === "pending"))
            
            // Add success message with workflow viewer
            return [...filtered, {
              id: Date.now().toString(),
              content: `Guide generated successfully!`,
              role: "assistant",
              timestamp: new Date(),
              status: "success",
              metadata: data,
              showWorkflow: true
            }]
          })
          
          toast({
            title: "Success!",
            description: data.message,
          })
        } else if (data.type === "error") {
          setStatusMessage("❌ " + data.message)
          setIsLoading(false)
          
          toast({
            title: "Error",
            description: data.message,
            variant: "destructive"
          })
        }
      }
      
      ws.onerror = (error) => {
        console.error("WebSocket error:", error)
      }
      
      ws.onclose = () => {
        console.log("WebSocket disconnected")
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }
      
      wsRef.current = ws
    }
    
    connectWebSocket()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [toast])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  const handleSubmit = async () => {
    if (!inputValue.trim() || isLoading) return
    
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      role: "user",
      timestamp: new Date(),
      status: "pending"
    }
    
    setMessages(prev => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)
    setStatusMessage("Processing your query...")
    
    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: inputValue
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Failed to process query")
      }
      
      const data = await response.json()
      
      // Success is handled by WebSocket, don't add duplicate message here
      // Just mark the user message as complete
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id 
          ? { ...msg, status: "success" } 
          : msg
      ))
      
    } catch (error: any) {
      setIsLoading(false)
      setStatusMessage("")
      
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: `Error: ${error.message}`,
        role: "assistant",
        timestamp: new Date(),
        status: "error"
      }
      
      setMessages(prev => [...prev, errorMessage])
      
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      })
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex flex-col min-h-screen relative overflow-hidden bg-black">
      <motion.div
        className="fixed pointer-events-none z-0"
        animate={{
          x: mousePosition.x,
          y: mousePosition.y,
        }}
        transition={{
          type: "spring",
          damping: 30,
          stiffness: 200,
          mass: 0.5,
        }}
        style={{
          transform: 'translate(-50%, -50%)',
        }}
      >
        <div className="relative w-[200px] h-[200px]">
          {/* Radial gradient circle */}
          <div className="absolute inset-0 rounded-full bg-gradient-radial from-orange-500/20 via-orange-500/5 to-transparent" />
          
          {/* Sparse dots scattered in the circle */}
          {Array.from({ length: 25 }).map((_, i) => {
            const angle = (i / 25) * Math.PI * 2
            const radius = 40 + Math.random() * 60
            const x = 100 + Math.cos(angle) * radius
            const y = 100 + Math.sin(angle) * radius
            const size = 1 + Math.random() * 2
            const opacity = 0.2 + Math.random() * 0.4
            
            return (
              <motion.div
                key={i}
                className="absolute rounded-full bg-orange-400"
                style={{
                  left: `${x}px`,
                  top: `${y}px`,
                  width: `${size}px`,
                  height: `${size}px`,
                  opacity: opacity,
                  filter: 'blur(0.5px)',
                }}
                animate={{
                  scale: [1, 1.2, 1],
                  opacity: [opacity, opacity * 1.5, opacity],
                }}
                transition={{
                  duration: 2 + Math.random() * 2,
                  repeat: Infinity,
                  delay: Math.random() * 2,
                }}
              />
            )
          })}
        </div>
      </motion.div>

      <div className="fixed inset-0 z-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
        }} />
      </div>

      {/* Messages Display - Full Height when has messages */}
      {hasMessages && (
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          <div className="max-w-5xl mx-auto space-y-6">
            {messages.map((message) => (
              <div key={message.id} className="space-y-4">
                <div className={`p-4 rounded-lg ${message.role === "user" ? "bg-orange-900/20 ml-8" : "bg-zinc-900/50"}`}>
                  <div className="text-sm text-zinc-400 mb-1">
                    {message.role === "user" ? "You" : "Assistant"}
                  </div>
                  <div className="text-white whitespace-pre-wrap">{message.content}</div>
                  {message.status === "pending" && (
                    <div className="mt-2 text-sm text-orange-400">Processing...</div>
                  )}
                  {message.status === "error" && (
                    <div className="mt-2 text-sm text-red-400">Error occurred</div>
                  )}
                </div>
                
                {/* Show Workflow Viewer */}
                {message.showWorkflow && message.metadata && (
                  <div className="mt-4">
                    <WorkflowViewer 
                      appName={message.metadata.app_name} 
                      taskName={message.metadata.task_name}
                    />
                  </div>
                )}
              </div>
            ))}
            {statusMessage && (
              <div className="p-4 rounded-lg bg-zinc-900/50 text-orange-400 text-sm">
                {statusMessage}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Input Section - Centered when no messages, bottom when has messages */}
      <div className={`w-full relative z-10 ${hasMessages ? 'border-t border-zinc-800 bg-black/50 backdrop-blur-sm' : 'flex items-center justify-center min-h-screen'}`}>
        <div className={`max-w-4xl mx-auto ${hasMessages ? 'py-4 px-4' : 'w-full px-4'}`}>

        {!hasMessages && (
          <div className="flex flex-row items-center mb-2">
            {/* Shader Circle */}
            <motion.div
              id="circle-ball"
              className="relative flex items-center justify-center z-10"
              animate={{
                y: isFocused ? 50 : 0,
                opacity: isFocused ? 0 : 100,
                filter: isFocused ? "blur(4px)" : "blur(0px)",
                rotation: isFocused ? 180 : 0,
              }}
            transition={{
              duration: 0.5,
              type: "spring",
              stiffness: 200,
              damping: 20,
            }}
          >
            <div className="z-10 absolute bg-white/5 h-11 w-11 rounded-full backdrop-blur-[3px]">
              <div className="h-[2px] w-[2px] bg-white rounded-full absolute top-4 left-4  blur-[1px]" />
              <div className="h-[2px] w-[2px] bg-white rounded-full absolute top-3 left-7  blur-[0.8px]" />
              <div className="h-[2px] w-[2px] bg-white rounded-full absolute top-8 left-2  blur-[1px]" />
              <div className="h-[2px] w-[2px] bg-white rounded-full absolute top-5 left-9 blur-[0.8px]" />
              <div className="h-[2px] w-[2px] bg-white rounded-full absolute top-7 left-7  blur-[1px]" />
            </div>
            <LiquidMetal
              style={{ height: 80, width: 80, filter: "blur(14px)", position: "absolute" }}
              colorBack="hsl(0, 0%, 0%, 0)"
              colorTint="hsl(29, 77%, 49%)"
              repetition={4}
              softness={0.5}
              shiftRed={0.3}
              shiftBlue={0.3}
              distortion={0.1}
              contour={1}
              shape="circle"
              offsetX={0}
              offsetY={0}
              scale={0.58}
              rotation={50}
              speed={5}
            />
            <LiquidMetal
              style={{ height: 80, width: 80 }}
              colorBack="hsl(0, 0%, 0%, 0)"
              colorTint="hsl(29, 77%, 49%)"
              repetition={4}
              softness={0.5}
              shiftRed={0.3}
              shiftBlue={0.3}
              distortion={0.1}
              contour={1}
              shape="circle"
              offsetX={0}
              offsetY={0}
              scale={0.58}
              rotation={50}
              speed={5}
            />
          </motion.div>

          {/* Greeting Text */}
            <motion.p
              className="text-white font-serif text-lg font-light z-10"
              animate={{
                y: isFocused ? 50 : 0,
                opacity: isFocused ? 0 : 100,
                filter: isFocused ? "blur(4px)" : "blur(0px)",
              }}
              transition={{
                duration: 0.5,
                type: "spring",
                stiffness: 200,
                damping: 20,
              }}
            >
              Hey there! What can I help you with today?      
            </motion.p>
          </div>
        )}

        <div className="relative">
          <motion.div
            className="absolute w-full h-full z-0 flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: isFocused ? 1 : 0 }}
            transition={{
              duration: 0.8, 
            }}
          >
            <PulsingBorder
              style={{ height: "146.5%", minWidth: "143%" }}
              colorBack="hsl(0, 0%, 0%)"
              roundness={0.18}
              thickness={0}
              softness={0}
              intensity={0.3}
              bloom={2}
              spots={2}
              spotSize={0.25}
              pulse={0}
              smoke={0.35}
              smokeSize={0.4}
              scale={0.7}
              rotation={0}
              offsetX={0}
              offsetY={0}
              speed={1}
              colors={[
                "hsl(29, 70%, 37%)",
                "hsl(32, 100%, 83%)",
                "hsl(4, 32%, 30%)",
                "hsl(25, 60%, 50%)",
                "hsl(0, 100%, 10%)",
              ]}
            />
          </motion.div>

          <motion.div
            className="relative bg-[#040404] rounded-2xl p-4 z-10"
            animate={{
              borderColor: isFocused ? "#BA9465" : "#3D3D3D",
            }}
            transition={{
              duration: 0.6,
              delay: 0.1,
            }}
            style={{
              borderWidth: "1px",
              borderStyle: "solid",
            }}
          >
            {/* Message Input */}
            <div className="relative mb-6">
              {!inputValue && (
                <div className="absolute top-3 left-3 pointer-events-none text-zinc-400 text-base">
                  {isLoading ? "Processing..." : "Type here... (e.g., 'How do I search for videos on YouTube?')"}
                </div>
              )}
              <Textarea
                placeholder=""
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                className="min-h-[60px] resize-none bg-transparent border-none text-white text-base placeholder:text-zinc-500 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:outline-none [&:focus]:ring-0 [&:focus]:outline-none [&:focus-visible]:ring-0 [&:focus-visible]:outline-none disabled:opacity-50"
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
              />
            </div>

            <div className="flex items-center justify-between">
              {/* Left side icons */}
              <div className="flex items-center gap-3">
                {/* Left side controls removed */}
              </div>

              {/* Right side icons */}
              <div className="flex items-center gap-3">
                <motion.div
                  whileHover={{ scale: isLoading ? 1 : 1.05 }}
                  whileTap={{ scale: isLoading ? 1 : 0.95 }}
                  transition={{ duration: 0.2 }}
                >
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSubmit}
                    disabled={isLoading || !inputValue.trim()}
                    className="h-12 w-12 rounded-full bg-gradient-to-br from-orange-400 via-orange-500 to-amber-500 hover:from-orange-300 hover:via-orange-400 hover:to-amber-400 text-white shadow-lg shadow-orange-400/30 hover:shadow-orange-300/50 transition-all duration-300 p-0 border border-orange-300/20 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? (
                      <Loader2 className="h-6 w-6 animate-spin" />
                    ) : (
                      <ArrowRightToLine className="h-6 w-6" />
                    )}
                  </Button>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
        </div>
      </div>
    </div>
  )
}
