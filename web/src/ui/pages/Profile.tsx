import React from "react"
import { useParams } from "react-router-dom"
import { api } from "../../api"

export default function Profile() {
  const { kind, handle } = useParams()
  const [data, setData] = React.useState<any>(null)

  React.useEffect(() => {
    if (!handle) return
    if (kind === 'agent') api.agentProfile(handle).then(setData).catch(()=>{})
    else api.userProfile(handle).then(setData).catch(()=>{})
  }, [kind, handle])

  return (
    <div className="card">
      <div className="hdr">
        <div style={{fontSize:18, fontWeight:700}}>@{data?.handle || handle}</div>
        <span className="pill">rep: {data?.reputation ?? 0}</span>
      </div>
      <div className="muted" style={{marginTop:6}}>{data?.bio || 'No bio yet.'}</div>
      {data?.origin_story && <div className="item" style={{marginTop:8}}><div style={{fontWeight:700}}>Origin story</div><div className="muted small" style={{marginTop:6}}>{data.origin_story}</div></div>}
      {Array.isArray(data?.badges) && data.badges.length > 0 && <div style={{display:"flex", gap:8, flexWrap:"wrap", marginTop:8}}>{data.badges.map((b: string) => <span key={b} className="pill">🏅 {b}</span>)}</div>}
      <div className="small" style={{marginTop:8}}>Bounties completed: <b>{data?.bounties_completed ?? 0}</b></div>
      <div className="list" style={{marginTop:10}}>
        {(data?.posts || []).map((p: any) => (
          <div className="item" key={p.id}><div className="muted small">Thread #{p.thread_id}</div>{p.content_md}</div>
        ))}
      </div>
    </div>
  )
}
