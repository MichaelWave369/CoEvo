import React from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../../api"
import { MeContext } from "../MeContext"

export default function Login() {
  const nav = useNavigate()
  const { setMe } = React.useContext(MeContext)
  const [mode, setMode] = React.useState<"login"|"register">("register")
  const [handle, setHandle] = React.useState("")
  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  async function submit() {
    setError(null)
    setBusy(true)
    try {
      if (mode === "register") {
        await api.register(handle, password, email || undefined)
      }
      await api.login(handle, password)
      const me = await api.me()
      setMe(me)
      nav("/")
    } catch (e: any) {
      setError(e.message || "Failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card" style={{maxWidth:520}}>
      <div className="hdr">
        <div style={{fontSize:18, fontWeight:700}}>
          {mode === "login" ? "Login" : "Create account"}
        </div>
        <button className="btn" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          Switch to {mode === "login" ? "Register" : "Login"}
        </button>
      </div>

      <div className="list">
        <div>
          <div className="muted small">Handle</div>
          <input className="input" value={handle} onChange={e=>setHandle(e.target.value)} placeholder="e.g. mikey" />
        </div>

        {mode === "register" && (
          <div>
            <div className="muted small">Email (optional)</div>
            <input className="input" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@domain.com" />
          </div>
        )}

        <div>
          <div className="muted small">Password</div>
          <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        </div>

        {error && <div className="item" style={{borderColor:"var(--danger)", color:"var(--danger)"}}>{error}</div>}

        <button className="btn primary" disabled={busy} onClick={submit}>
          {busy ? "Working..." : (mode === "login" ? "Login" : "Register + Login")}
        </button>

        <div className="muted small">
          New accounts get a starter grant (default rewards).
        </div>
      </div>
    </div>
  )
}
