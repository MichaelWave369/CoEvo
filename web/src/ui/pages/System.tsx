import React from "react"
import { api } from "../../api"

export default function System() {
  const [pub, setPub] = React.useState<string>("")
  const [msg, setMsg] = React.useState<string | null>(null)

  React.useEffect(() => {
    api.publicKey().then(d => setPub(d.public_key_pem || "")).catch(()=>{})
  }, [])

  function copy() {
    navigator.clipboard.writeText(pub)
    setMsg("Copied.")
    setTimeout(()=>setMsg(null), 1200)
  }

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>System</div>
          <span className="badge">audit</span>
        </div>

        <div className="item">
          <div style={{fontWeight:700}}>Node public key</div>
          <div className="muted small">Used to verify signed posts + ledger tx + event logs.</div>
          <pre style={{whiteSpace:"pre-wrap"}}>{pub || "—"}</pre>
          <button className="btn" onClick={copy} disabled={!pub}>Copy</button>
          {msg && <span className="muted small" style={{marginLeft:10}}>{msg}</span>}
        </div>

        <div className="item">
          <div style={{fontWeight:700}}>Signed audit export</div>
          <div className="muted small">Admins/mods can export posts + ledger + events + notifications as a zip.</div>
          <a className="btn primary" href={api.auditExportUrl()}>Download audit export</a>
        </div>
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:6}}>Admin notes</div>
        <div className="muted small">
          Seed admin by setting:<br/>
          <span className="kbd">COEVO_SEED_ADMIN=1</span><br/>
          <span className="kbd">COEVO_ADMIN_PASSWORD=...</span>
        </div>
      </div>
    </div>
  )
}
