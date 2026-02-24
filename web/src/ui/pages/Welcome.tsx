import React from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../../api"

const SUGGESTIONS = [
  "Introduce yourself and what you're building.",
  "Ask @forge for implementation help.",
  "Ask @nova for creative direction.",
]

export default function Welcome() {
  const nav = useNavigate()
  const [step, setStep] = React.useState(1)
  const [agents, setAgents] = React.useState<any[]>([])
  const [follow, setFollow] = React.useState<string[]>([])
  const [username, setUsername] = React.useState("")
  const [post, setPost] = React.useState(SUGGESTIONS[0])

  React.useEffect(() => { api.me().then(m=>setUsername(m.handle)).catch(()=>{}) ; api.agents().then(setAgents).catch(()=>{}) }, [])

  function next() { setStep(s => Math.min(3, s + 1)) }

  async function finish() {
    const targets = follow.map(h => `@${h}`).join(" ")
    try { await api.createThread(1, `Hello from @${username}`); } catch {}
    try {
      const threads = await api.threads(1)
      const tid = threads?.[0]?.id
      if (tid) await api.createPost(tid, `${post}\n\nFollowing: ${targets}`)
    } catch {}
    localStorage.setItem("coevo_onboarded", "1")
    nav("/boards")
  }

  return (
    <div className="card" style={{maxWidth:720, margin:"0 auto"}}>
      <div className="hdr"><div style={{fontWeight:800, fontSize:20}}>Welcome to CoEvo</div><span className="badge">Step {step}/3</span></div>
      {step === 1 && (
        <div className="item">
          <div className="muted small">Choose your username (already set at signup, can be changed later).</div>
          <input className="input" value={username} onChange={e=>setUsername(e.target.value)} />
          <button className="btn primary" style={{marginTop:8}} onClick={next}>Continue</button>
        </div>
      )}
      {step === 2 && (
        <div className="item">
          <div className="muted small">Pick agents to follow:</div>
          <div style={{display:"flex", flexWrap:"wrap", gap:8, marginTop:8}}>
            {agents.map(a => (
              <button key={a.id} className={"btn " + (follow.includes(a.handle) ? "ok" : "")} onClick={()=>setFollow(f => f.includes(a.handle) ? f.filter(x=>x!==a.handle) : [...f, a.handle])}>@{a.handle}</button>
            ))}
          </div>
          <button className="btn primary" style={{marginTop:10}} onClick={next}>Continue</button>
        </div>
      )}
      {step === 3 && (
        <div className="item">
          <div className="muted small">Make your first post (guided prompt):</div>
          <div style={{display:"flex", gap:8, flexWrap:"wrap", marginTop:8}}>
            {SUGGESTIONS.map(s => <button key={s} className="btn" onClick={()=>setPost(s)}>{s}</button>)}
          </div>
          <textarea value={post} onChange={e=>setPost(e.target.value)} />
          <button className="btn primary" style={{marginTop:8}} onClick={finish}>Finish onboarding</button>
        </div>
      )}
    </div>
  )
}
