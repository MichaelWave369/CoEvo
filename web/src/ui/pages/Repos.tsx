import React from "react"
import { api } from "../../api"

export default function Repos() {
  const [list, setList] = React.useState<any[]>([])
  const [url, setUrl] = React.useState("")
  const [title, setTitle] = React.useState("")
  const [desc, setDesc] = React.useState("")
  const [tags, setTags] = React.useState("")
  const [msg, setMsg] = React.useState<string | null>(null)

  async function refresh() {
    const d = await api.repos()
    setList(d)
  }
  React.useEffect(() => { refresh().catch(()=>{}) }, [])

  async function add() {
    setMsg(null)
    try {
      const tagList = tags.split(",").map(t=>t.trim()).filter(Boolean)
      await api.addRepo(url, title, desc, tagList)
      setUrl(""); setTitle(""); setDesc(""); setTags("")
      setMsg("Added.")
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>Repos</div>
          <span className="badge">links</span>
        </div>

        <div className="item">
          <div style={{fontWeight:700, marginBottom:8}}>Add repo link</div>
          <div className="list">
            <input className="input" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://github.com/user/repo" />
            <input className="input" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Title (optional)" />
            <input className="input" value={desc} onChange={e=>setDesc(e.target.value)} placeholder="Description (optional)" />
            <input className="input" value={tags} onChange={e=>setTags(e.target.value)} placeholder="tags comma-separated" />
            <button className="btn primary" onClick={add} disabled={!url.trim()}>Add</button>
            {msg && <div className="muted small">{msg}</div>}
          </div>
        </div>

        <div className="list">
          {list.map(r => (
            <div className="item" key={r.id}>
              <div style={{fontWeight:700}}><a href={r.url} target="_blank" rel="noreferrer">{r.title || r.url}</a></div>
              {r.description && <div className="muted small">{r.description}</div>}
              {r.tags?.length ? <div className="muted small">tags: {r.tags.join(", ")}</div> : null}
            </div>
          ))}
          {list.length === 0 && <div className="muted small">No repos yet.</div>}
        </div>
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:6}}>Use cases</div>
        <div className="muted small">
          • share a project repo<br/>
          • link a zip artifact thread<br/>
          • attach bounties to issues
        </div>
      </div>
    </div>
  )
}
