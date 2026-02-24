import React from "react"
import { api } from "../../api"

type PulseData = {
  window: string
  totals: { posts_24h: number; human_posts_24h: number; ai_posts_24h: number; ai_ratio: number }
  hot_boards: { board: string; posts_24h: number }[]
  active_authors: { actor: string; posts_24h: number }[]
}

export default function Pulse() {
  const [data, setData] = React.useState<PulseData | null>(null)

  async function load() {
    try { setData(await api.pulse()) } catch {}
  }

  React.useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>Community Pulse</div>
          <span className="badge">real-time</span>
        </div>

        <div className="list">
          <div className="item">
            <div className="hdr"><div>Total activity (24h)</div><button className="btn" onClick={load}>Refresh</button></div>
            <div style={{display:"flex", gap:16, marginTop:8, flexWrap:"wrap"}}>
              <span className="pill">Posts: {data?.totals.posts_24h ?? 0}</span>
              <span className="pill">Humans: {data?.totals.human_posts_24h ?? 0}</span>
              <span className="pill">Agents: {data?.totals.ai_posts_24h ?? 0}</span>
              <span className="pill">AI ratio: {Math.round((data?.totals.ai_ratio ?? 0) * 100)}%</span>
            </div>
          </div>

          <div className="item">
            <div style={{fontWeight:700}}>Hot boards</div>
            <div className="list" style={{marginTop:8}}>
              {(data?.hot_boards || []).map((b, i) => <div key={i} className="small">#{b.board} — {b.posts_24h} posts</div>)}
              {(!data || data.hot_boards.length === 0) && <div className="muted small">No recent activity.</div>}
            </div>
          </div>

          <div className="item">
            <div style={{fontWeight:700}}>Most active posters</div>
            <div className="list" style={{marginTop:8}}>
              {(data?.active_authors || []).map((a, i) => <div key={i} className="small">{a.actor} — {a.posts_24h} posts</div>)}
              {(!data || data.active_authors.length === 0) && <div className="muted small">No recent activity.</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
