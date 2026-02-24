import React from "react"
import { api } from "../../api"

export default function Votes() {
  const [list, setList] = React.useState<any[]>([])
  const [title, setTitle] = React.useState("Improve platform")
  const [details, setDetails] = React.useState("")

  async function load() {
    try { setList(await api.votes()) } catch {}
  }

  React.useEffect(() => { load() }, [])

  async function propose() {
    await api.createVote(title, "feature", details)
    setDetails("")
    load()
  }

  async function cast(id: number, vote: "yes" | "no") {
    await api.castVote(id, vote, "")
    load()
  }

  return (
    <div className="card">
      <div className="hdr"><div style={{fontWeight:700, fontSize:18}}>Community Governance</div><span className="badge">/vote</span></div>
      <div className="item">
        <div className="muted small">Propose platform changes, board ideas, or feature requests.</div>
        <input className="input" value={title} onChange={e=>setTitle(e.target.value)} />
        <textarea value={details} onChange={e=>setDetails(e.target.value)} placeholder="Details" />
        <button className="btn primary" onClick={propose}>Propose</button>
      </div>
      <div className="list" style={{marginTop:10}}>
        {list.map(v => (
          <div className="item" key={v.id}>
            <div style={{fontWeight:700}}>{v.title}</div>
            <div className="muted small">yes {v.yes} • no {v.no}</div>
            <div style={{display:"flex", gap:8, marginTop:8}}>
              <button className="btn ok" onClick={()=>cast(v.id, "yes")}>Vote yes</button>
              <button className="btn danger" onClick={()=>cast(v.id, "no")}>Vote no</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
