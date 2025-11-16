import { ChatInterface } from "@/components/chat-interface"

export default function Home() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 120% 80% at 50% 120%, #94a3b8 0%, #334155 40%, #1e293b 60%, #0f172a 80%, #050815 100%)'
        }}
      />
      <div className="relative z-10">
        <ChatInterface />
      </div>
    </div>
  )
}
