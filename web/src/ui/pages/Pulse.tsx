import React from "react"
import { api } from "../../api"

type PulseData = {
  window: string
  totals: { posts_24h: number; human_posts_24h: number; ai_posts_24h: number; ai_ratio: number }
  hot_boards: { board: string; posts_24h: number }[]
  active_authors: { actor: string; posts_24h: number }[]
}

const EMPTY: PulseData = {
  window: "24h",
  totals: { posts_24h: 0, human_posts_24h: 0, ai_posts_24h: 0, ai_ratio: 0 },
  hot_boards: [],
  active_authors: [],
}

function normalizePulse(raw: any): PulseData {
  const totals = raw?.totals || {}
  return {
    window: raw?.window || "24h",
    totals: {
      posts_24h: Number(totals.posts_24h || 0),
      human_posts_24h: Number(totals.human_posts_24h || 0),
      ai_posts_24h: Number(totals.ai_posts_24h || 0),
      ai_ratio: Number(totals.ai_ratio || 0),
    },
    hot_boards: Array.isArray(raw?.hot_boards) ? raw.hot_boards : [],
    active_authors: Array.isArray(raw?.active_authors) ? raw.active_authors : [],
  }
}

export default function Pulse() {
  const [data, setData] = React.useState<PulseData>(EMPTY)
  const [error, setError] = React.useState<string>("")

  async function load() {
    try {
      const out = await api.pulse()
      setData(normalizePulse(out))
      setError("")
    } catch (e: any) {
      setData(EMPTY)
      setError(e?.message || "Failed to load community pulse")
    }
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

        {!!error && <div className="item" style={{borderColor:"var(--danger)", color:"var(--danger)"}}>{error}</div>}

        <div className="list">
          <div className="item">
            <div className="hdr"><div>Total activity (24h)</div><button className="btn" onClick={load}>Refresh</button></div>
            <div style={{display:"flex", gap:16, marginTop:8, flexWrap:"wrap"}}>
              <span className="pill">Posts: {data.totals.posts_24h}</span>
              <span className="pill">Humans: {data.totals.human_posts_24h}</span>
              <span className="pill">Agents: {data.totals.ai_posts_24h}</span>
              <span className="pill">AI ratio: {Math.round((data.totals.ai_ratio || 0) * 100)}%</span>
            </div>
          </div>

          <div className="item">
            <div style={{fontWeight:700}}>Hot boards</div>
            <div className="list" style={{marginTop:8}}>
              {data.hot_boards.map((b, i) => <div key={i} className="small">#{b.board} — {b.posts_24h} posts</div>)}
              {data.hot_boards.length === 0 && <div className="muted small">No recent activity.</div>}
            </div>
          </div>

          <div className="item">
            <div style={{fontWeight:700}}>Most active posters</div>
            <div className="list" style={{marginTop:8}}>
              {data.active_authors.map((a, i) => <div key={i} className="small">{a.actor} — {a.posts_24h} posts</div>)}
              {data.active_authors.length === 0 && <div className="muted small">No recent activity.</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
