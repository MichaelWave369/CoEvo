import React from "react"
import { Link, useParams } from "react-router-dom"
import { api } from "../../api"

export default function Board() {
  const { boardId } = useParams()
  const id = Number(boardId)
  const [threads, setThreads] = React.useState<any[]>([])
  const [title, setTitle] = React.useState("")
  const [err, setErr] = React.useState<string | null>(null)

  async function refresh() {
    setErr(null)
    try {
      const t = await api.threads(id)
      setThreads(t)
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  React.useEffect(() => { refresh() }, [boardId])

  async function create() {
    setErr(null)
    try {
      await api.createThread(id, title)
      setTitle("")
      await refresh()
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>Threads</div>
          <Link className="btn" to="/">Back</Link>
        </div>

        <div className="item">
          <div className="muted small">New thread title</div>
          <div style={{display:"flex", gap:8, marginTop:6}}>
            <input className="input" value={title} onChange={e=>setTitle(e.target.value)} placeholder="What are we building today?" />
            <button className="btn primary" onClick={create} disabled={!title.trim()}>Create</button>
          </div>
          <div className="muted small" style={{marginTop:6}}>
            Tip: In <span className="kbd">help</span>, mention <span className="kbd">@sage</span>.
          </div>
        </div>

        {err && <div className="item" style={{borderColor:"var(--danger)", color:"var(--danger)"}}>{err}</div>}

        <div className="list" style={{marginTop:10}}>
          {threads.map(t => (
            <div className="item" key={t.id}>
              <div style={{display:"flex", justifyContent:"space-between", gap:12}}>
                <div style={{fontWeight:700}}>
                  <Link to={`/threads/${t.id}`}>{t.title}</Link>
                </div>
                <Link className="btn" to={`/threads/${t.id}`}>Open</Link>
              </div>
            </div>
          ))}
          {threads.length === 0 && <div className="muted small">No threads yet.</div>}
        </div>
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:6}}>Thread tools</div>
        <div className="muted small">
          • Watch to get notified<br/>
          • Live posts (SSE)<br/>
          • Bounties + escrow<br/>
          • Upload artifacts<br/>
          • Link repos
        </div>
      </div>
    </div>
  )
}
