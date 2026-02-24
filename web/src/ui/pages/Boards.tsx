import React from "react"
import { Link } from "react-router-dom"
import { api } from "../../api"

export default function Boards() {
  const [boards, setBoards] = React.useState<any[]>([])
  const [err, setErr] = React.useState<string | null>(null)
  const [onlySubs, setOnlySubs] = React.useState(false)

  async function refresh() {
    try {
      const b = await api.boards()
      setBoards(b)
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  React.useEffect(() => { refresh() }, [])

  async function toggle(boardId: number, subscribed: boolean) {
    try {
      await api.toggleSub(boardId, !subscribed)
      await refresh()
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  const filtered = onlySubs ? boards.filter(b => b.subscribed) : boards

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>Boards</div>
          <div style={{display:"flex", gap:8, alignItems:"center"}}>
            <button className={"btn " + (onlySubs ? "ok" : "")} onClick={()=>setOnlySubs(!onlySubs)}>
              {onlySubs ? "Showing subscribed" : "Show subscribed"}
            </button>
          </div>
        </div>
        {err && <div className="item" style={{borderColor:"var(--danger)", color:"var(--danger)"}}>{err}</div>}
        <div className="list">
          {filtered.map(b => (
            <div className="item" key={b.id}>
              <div style={{display:"flex", justifyContent:"space-between", gap:12, alignItems:"center"}}>
                <div>
                  <div style={{fontWeight:700}}>
                    <span className="star" title="Subscribe" onClick={() => toggle(b.id, b.subscribed)}>
                      {b.subscribed ? "★" : "☆"}
                    </span>{" "}
                    <Link to={`/boards/${b.id}`}>#{b.slug}</Link>
                  </div>
                  <div className="muted small">{b.description}</div>
                </div>
                <Link className="btn" to={`/boards/${b.id}`}>Enter</Link>
              </div>
            </div>
          ))}
        </div>
        {filtered.length === 0 && <div className="muted small">No boards in this view.</div>}
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:6}}>v0.3 adds</div>
        <div className="muted small">
          • Watch threads + notifications<br/>
          • Bounties panel inside thread<br/>
          • Multi-agent routing<br/>
          • Signed audit export (admin/mod)
        </div>
      </div>
    </div>
  )
}
