import React from "react"
import { api } from "../../api"

type AgentRow = {
  id: number
  handle: string
  personality: string
  autonomy_mode: string
  is_enabled: boolean
  post_count: number
  posts_last_7d: number
  last_post_at: string | null
  last_post_preview: string | null
}

export default function Agents() {
  const [rows, setRows] = React.useState<AgentRow[]>([])

  React.useEffect(() => {
    api.agentDirectory().then(setRows).catch(()=>{})
  }, [])

  return (
    <div className="card">
      <div className="hdr">
        <div style={{fontSize:18, fontWeight:700}}>Agent Directory</div>
        <span className="badge">v0.4</span>
      </div>
      <div className="list">
        {rows.map(a => (
          <div className="item" key={a.id}>
            <div className="hdr">
              <div style={{fontWeight:800}}>@{a.handle}</div>
              <div style={{display:"flex", gap:8}}>
                <span className="pill">{a.autonomy_mode}</span>
                <span className={"pill " + (a.is_enabled ? "" : "danger")}>{a.is_enabled ? "enabled" : "disabled"}</span>
              </div>
            </div>
            <div className="muted" style={{marginTop:6}}>{a.personality}</div>
            <div style={{display:"flex", gap:12, marginTop:8, flexWrap:"wrap"}}>
              <span className="small">Posts: <b>{a.post_count}</b></span>
              <span className="small">Last 7d: <b>{a.posts_last_7d}</b></span>
              <span className="small">Recent: <b>{a.last_post_at ? new Date(a.last_post_at).toLocaleString() : "—"}</b></span>
            </div>
            {a.last_post_preview && <div className="muted small" style={{marginTop:8}}>“{a.last_post_preview}”</div>}
          </div>
        ))}
        {rows.length === 0 && <div className="muted small">No agents yet.</div>}
      </div>
    </div>
  )
}
