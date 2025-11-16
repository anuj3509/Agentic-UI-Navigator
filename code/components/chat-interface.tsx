"use client"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Brain, Link, Folder, ArrowRight, ArrowRightToLine } from 'lucide-react'
import { LiquidMetal, PulsingBorder } from "@paper-design/shaders-react"
import { motion } from "framer-motion"
import { useState, useEffect } from "react"

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
}

export function ChatInterface() {
  const [isFocused, setIsFocused] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 relative overflow-hidden">
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

      <div className="w-full max-w-4xl relative z-10">
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
                  Type here...
                </div>
              )}
              <Textarea
                placeholder=""
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="min-h-[60px] resize-none bg-transparent border-none text-white text-base placeholder:text-zinc-500 focus:ring-0 focus:outline-none focus-visible:ring-0 focus-visible:outline-none [&:focus]:ring-0 [&:focus]:outline-none [&:focus-visible]:ring-0 [&:focus-visible]:outline-none"
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
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                >
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-12 w-12 rounded-full bg-gradient-to-br from-orange-400 via-orange-500 to-amber-500 hover:from-orange-300 hover:via-orange-400 hover:to-amber-400 text-white shadow-lg shadow-orange-400/30 hover:shadow-orange-300/50 transition-all duration-300 p-0 border border-orange-300/20"
                  >
                    <ArrowRightToLine className="h-6 w-6" />
                  </Button>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
