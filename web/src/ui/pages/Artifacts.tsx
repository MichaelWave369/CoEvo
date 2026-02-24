import React from "react"
import { api } from "../../api"

export default function Artifacts() {
  const [list, setList] = React.useState<any[]>([])
  const [msg, setMsg] = React.useState<string | null>(null)

  async function refresh() {
    const d = await api.artifacts()
    setList(d)
  }

  React.useEffect(() => { refresh().catch(()=>{}) }, [])

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setMsg(null)
    try {
      await api.uploadArtifact(file)
      setMsg("Uploaded.")
      await refresh()
    } catch (err: any) {
      setMsg(err.message || "Failed")
    } finally {
      e.target.value = ""
    }
  }

  return (
    <div className="card">
      <div className="hdr">
        <div style={{fontSize:18, fontWeight:700}}>Artifacts</div>
        <label className="btn primary">
          Upload
          <input type="file" style={{display:"none"}} onChange={upload} />
        </label>
      </div>
      {msg && <div className="muted small">{msg}</div>}
      <div className="list">
        {list.map(a => (
          <div className="item" key={a.id}>
            <div style={{display:"flex", justifyContent:"space-between", gap:12}}>
              <div>
                <div style={{fontWeight:700}}>{a.filename}</div>
                <div className="muted small">{a.mime} • {a.size_bytes} bytes</div>
                <div className="muted small">sha256 {a.sha256.slice(0,12)}…</div>
              </div>
              <a className="btn" href={api.downloadArtifactUrl(a.id)}>Download</a>
            </div>
          </div>
        ))}
        {list.length === 0 && <div className="muted small">No uploads yet.</div>}
      </div>
    </div>
  )
}
