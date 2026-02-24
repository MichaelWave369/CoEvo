import React from "react"
import { api } from "../../api"
import { Link } from "react-router-dom"

export default function Bounties() {
  const [list, setList] = React.useState<any[]>([])
  const [msg, setMsg] = React.useState<string | null>(null)

  async function refresh() {
    const d = await api.bounties()
    setList(d)
  }
  React.useEffect(() => { refresh().catch(()=>{}) }, [])

  async function claim(id: number) {
    setMsg(null)
    try {
      await api.claimBounty(id)
      setMsg("Claimed.")
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  async function submit(id: number) {
    const note = prompt("Submission note (what did you deliver?)") || ""
    if (!note.trim()) return
    setMsg(null)
    try {
      await api.submitBounty(id, note)
      setMsg("Submitted.")
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  async function pay(id: number, accept: boolean) {
    setMsg(null)
    try {
      await api.payBounty(id, accept)
      setMsg(accept ? "Paid." : "Refunded.")
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  return (
    <div className="card">
      <div className="hdr">
        <div style={{fontSize:18, fontWeight:700}}>Bounties</div>
        <span className="badge">escrow → payout</span>
      </div>
      {msg && <div className="muted small">{msg}</div>}

      <div className="list">
        {list.map(b => (
          <div className="item" key={b.id}>
            <div style={{display:"flex", justifyContent:"space-between", gap:12}}>
              <div>
                <div style={{fontWeight:800}}>{b.title} <span className="muted small">#{b.id}</span></div>
                <div className="muted small">amount {b.amount} • status <span className="kbd">{b.status}</span></div>
                <div className="muted small">thread <Link to={`/threads/${b.thread_id}`}>#{b.thread_id}</Link></div>
              </div>
              <div style={{display:"flex", flexDirection:"column", gap:6, minWidth:170}}>
                {b.status === "open" && <button className="btn primary" onClick={()=>claim(b.id)}>Claim</button>}
                {b.status === "claimed" && <button className="btn" onClick={()=>submit(b.id)}>Submit</button>}
                {b.status === "submitted" && (
                  <>
                    <button className="btn ok" onClick={()=>pay(b.id, true)}>Creator: Pay</button>
                    <button className="btn danger" onClick={()=>pay(b.id, false)}>Creator: Refund</button>
                  </>
                )}
              </div>
            </div>
            {b.requirements_md && (
              <div className="muted small" style={{marginTop:8, whiteSpace:"pre-wrap"}}>{b.requirements_md}</div>
            )}
          </div>
        ))}
        {list.length === 0 && <div className="muted small">No bounties yet.</div>}
      </div>
    </div>
  )
}
