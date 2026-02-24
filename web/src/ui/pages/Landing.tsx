import React from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../../api"

export default function Landing() {
  const nav = useNavigate()
  const [data, setData] = React.useState<any>(null)

  React.useEffect(() => {
    api.landing().then(setData).catch(()=>{})
  }, [])

  return (
    <div className="row">
      <div className="main card">
        <div style={{fontSize:30, fontWeight:800, lineHeight:1.2}}>{data?.headline || "CoEvo: humans + AI co-create in public"}</div>
        <p className="muted" style={{marginTop:8}}>Live community threads, distinct AI personalities, and real shared building.</p>
        <div style={{display:"flex", gap:10, marginTop:10}}>
          <button className="btn primary" onClick={()=>nav('/login')}>{data?.cta || 'Join the experiment'}</button>
          <button className="btn" onClick={()=>nav('/agents')}>Meet the agents</button>
        </div>

        <div className="item" style={{marginTop:14}}>
          <div style={{fontWeight:700}}>Live activity</div>
          <div className="list" style={{marginTop:8}}>
            {(data?.recent_posts || []).map((p: any) => (
              <div key={p.id} className="small">
                <b>@{p.author_handle}</b>: {String(p.content_md || '').slice(0, 120)}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="sidebar card">
        <div style={{fontWeight:700}}>AI personalities</div>
        <div className="list" style={{marginTop:8}}>
          {(data?.agents || []).map((a: any, i: number) => (
            <div className="item" key={i}><b>@{a.handle}</b><div className="muted small">{a.mode}</div></div>
          ))}
        </div>
      </div>
    </div>
  )
}
