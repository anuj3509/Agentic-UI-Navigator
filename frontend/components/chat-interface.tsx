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
  const hasAddedWorkflow = useRef(false)

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
          
          // Only add workflow once (prevent duplicates from multiple WebSocket messages)
          if (!hasAddedWorkflow.current) {
            hasAddedWorkflow.current = true
            
            // Update the last user message to add workflow viewer
            setMessages(prev => {
              // Remove any "Processing..." assistant message
              const filtered = prev.filter(msg => !(msg.role === "assistant" && msg.status === "pending"))
              
              // Check if workflow already exists
              const hasWorkflow = filtered.some(msg => msg.showWorkflow)
              if (hasWorkflow) return filtered
              
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
          }
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
    
    // Reset workflow flag for new query
    hasAddedWorkflow.current = false
    
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
    <div className="flex flex-col min-h-screen relative overflow-hidden">
      {/* Animated gradient orbs in background */}
      <div className="fixed inset-0 z-0 overflow-hidden">
        <motion.div
          className="absolute top-0 -right-40 w-96 h-96 bg-orange-500/20 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.3, 0.2],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute -bottom-40 -left-40 w-96 h-96 bg-amber-500/20 rounded-full blur-3xl"
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.15, 0.25, 0.15],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 w-[500px] h-[500px] bg-orange-600/10 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.1, 0.2, 0.1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      </div>

      {/* Cursor follow effect */}
      <motion.div
        className="fixed pointer-events-none z-0 w-[250px] h-[250px]"
        animate={{
          x: mousePosition.x - 125,
          y: mousePosition.y - 125,
        }}
        transition={{
          type: "spring",
          damping: 25,
          stiffness: 150,
          mass: 0.3,
        }}
      >
        {/* Radial gradient circle */}
        <div className="absolute inset-0 rounded-full bg-gradient-radial from-orange-500/30 via-orange-500/10 to-transparent" />
        
        {/* Sparse dots scattered in the circle */}
        {Array.from({ length: 20 }).map((_, i) => {
          const angle = (i / 20) * Math.PI * 2
          const radius = 50 + Math.random() * 70
          const x = 125 + Math.cos(angle) * radius - 2.5
          const y = 125 + Math.sin(angle) * radius - 2.5
          const size = 2.5 + Math.random() * 2.5
          const opacity = 0.4 + Math.random() * 0.4
          
          return (
            <motion.div
              key={i}
              className="absolute rounded-full bg-gradient-to-br from-orange-400 to-amber-500"
              style={{
                left: `${x}px`,
                top: `${y}px`,
                width: `${size}px`,
                height: `${size}px`,
                opacity: opacity,
                filter: 'blur(0.8px)',
                boxShadow: '0 0 4px rgba(251, 146, 60, 0.6)',
              }}
              animate={{
                scale: [1, 1.4, 1],
                opacity: [opacity, opacity * 1.5, opacity],
                x: [0, Math.cos(angle) * 8, 0],
                y: [0, Math.sin(angle) * 8, 0],
              }}
              transition={{
                duration: 3 + Math.random() * 2,
                repeat: Infinity,
                delay: Math.random() * 2,
                ease: "easeInOut",
              }}
            />
          )
        })}
      </motion.div>

      {/* Grid pattern overlay */}
      <div className="fixed inset-0 z-0 opacity-[0.03]">
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle, rgba(251, 146, 60, 0.4) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
        }} />
      </div>

      {/* Messages Display - Full Height when has messages */}
      {hasMessages && (
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          <div className="max-w-5xl mx-auto space-y-6">
            {messages.map((message) => (
              <motion.div 
                key={message.id} 
                className="space-y-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <div className={`p-5 rounded-xl backdrop-blur-sm border ${
                  message.role === "user" 
                    ? "bg-gradient-to-br from-orange-500/15 to-amber-500/10 border-orange-500/20 ml-8 shadow-lg shadow-orange-500/5" 
                    : "bg-slate-900/60 border-slate-700/50 shadow-xl"
                }`}>
                  <div className="text-xs font-medium text-orange-400/80 mb-2 tracking-wide uppercase">
                    {message.role === "user" ? "You" : "🤖 AI Assistant"}
                  </div>
                  <div className="text-white/95 whitespace-pre-wrap leading-relaxed">{message.content}</div>
                  {message.status === "pending" && (
                    <div className="mt-3 text-sm text-orange-400 flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Processing...
                    </div>
                  )}
                  {message.status === "error" && (
                    <div className="mt-3 text-sm text-red-400 flex items-center gap-2">
                      ⚠️ Error occurred
                    </div>
                  )}
                </div>
                
                {/* Show Workflow Viewer */}
                {message.showWorkflow && message.metadata && (
                  <motion.div 
                    className="mt-4"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                  >
                    <WorkflowViewer 
                      appName={message.metadata.app_name} 
                      taskName={message.metadata.task_name}
                    />
                  </motion.div>
                )}
              </motion.div>
            ))}
            {statusMessage && (
              <motion.div 
                className="p-4 rounded-xl bg-slate-900/70 backdrop-blur-sm border border-orange-500/30 text-orange-400 text-sm shadow-lg"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                {statusMessage}
              </motion.div>
            )}
          </div>
        </div>
      )}

      {/* Input Section - Centered when no messages, bottom when has messages */}
      <div className={`w-full relative z-10 ${hasMessages ? 'border-t border-orange-500/10 bg-gradient-to-b from-slate-900/80 to-slate-950/90 backdrop-blur-xl shadow-2xl' : 'flex items-center justify-center min-h-screen'}`}>
        <div className={`max-w-4xl mx-auto ${hasMessages ? 'py-6 px-4' : 'w-full px-4'}`}>

        {!hasMessages && (
          <div className="mb-12 text-center">
            {/* Title Section */}
            <motion.div
              className="mb-24 -mt-16"
              animate={{
                y: isFocused ? -20 : 0,
                opacity: isFocused ? 0.3 : 1,
                filter: isFocused ? "blur(2px)" : "blur(0px)",
              }}
              transition={{
                duration: 0.5,
                type: "spring",
                stiffness: 200,
                damping: 20,
              }}
            >
              <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-orange-400 via-amber-400 to-orange-500 bg-clip-text text-transparent">
                Agentic UI Navigator
              </h1>
              <p className="text-slate-400 text-lg max-w-2xl mx-auto">
                AI-powered automation for web guides
              </p>
            </motion.div>

            {/* Avatar and Greeting */}
            <div className="flex flex-row items-center justify-center mb-4">
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
                className="text-white/90 font-serif text-xl font-light z-10 ml-4"
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
          </div>
        )}

        <div className="relative">
          <motion.div
            className="absolute w-full h-full z-0 flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: isFocused ? 1 : 0 }}
            transition={{
              duration: 0.6, 
            }}
          >
            <PulsingBorder
              style={{ height: "115%", minWidth: "102%" }}
              colorBack="hsl(0, 0%, 0%, 0)"
              roundness={0.18}
              thickness={0}
              softness={0}
              intensity={0.4}
              bloom={2}
              spots={3}
              spotSize={0.3}
              pulse={0}
              smoke={0.4}
              smokeSize={0.5}
              scale={0.75}
              rotation={0}
              offsetX={0}
              offsetY={0}
              speed={1.2}
              colors={[
                "hsl(29, 80%, 50%)",
                "hsl(35, 100%, 60%)",
                "hsl(20, 70%, 45%)",
                "hsl(40, 90%, 55%)",
              ]}
            />
          </motion.div>

          <motion.div
            className="relative bg-gradient-to-br from-slate-900/90 to-slate-800/80 rounded-2xl p-5 z-10 shadow-2xl backdrop-blur-xl border"
            animate={{
              borderColor: isFocused ? "rgba(251, 146, 60, 0.5)" : "rgba(71, 85, 105, 0.3)",
              boxShadow: isFocused 
                ? "0 0 30px rgba(251, 146, 60, 0.2), 0 20px 60px rgba(251, 146, 60, 0.1)"
                : "0 20px 40px rgba(0, 0, 0, 0.4)",
            }}
            transition={{
              duration: 0.4,
            }}
          >
            {/* Message Input */}
            <div className="relative mb-6">
              {!inputValue && (
                <div className="absolute top-3 left-3 pointer-events-none text-slate-400/60 text-base">
                  {isLoading ? (
                    <span className="text-orange-400">🤖 Processing your request...</span>
                  ) : (
                    <span>Ask me anything... <span className="text-orange-400/70">e.g., "How do I search for videos on YouTube?"</span></span>
                  )}
                </div>
              )}
              <Textarea
                placeholder=""
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                className="min-h-[60px] resize-none bg-transparent border-none text-white/95 text-base placeholder:text-slate-400 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:outline-none [&:focus]:ring-0 [&:focus]:outline-none [&:focus-visible]:ring-0 [&:focus-visible]:outline-none disabled:opacity-50"
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
                    className="h-12 w-12 rounded-full bg-gradient-to-br from-orange-500 via-orange-600 to-amber-600 hover:from-orange-400 hover:via-orange-500 hover:to-amber-500 text-white shadow-xl shadow-orange-500/40 hover:shadow-2xl hover:shadow-orange-400/60 transition-all duration-300 p-0 border border-orange-400/30 hover:border-orange-300/50 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none hover:scale-105 active:scale-95"
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
