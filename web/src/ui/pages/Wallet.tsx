import React from "react"
import { api } from "../../api"

export default function Wallet() {
  const [data, setData] = React.useState<any>(null)
  const [to, setTo] = React.useState("")
  const [amount, setAmount] = React.useState(5)
  const [msg, setMsg] = React.useState<string | null>(null)

  async function refresh() {
    const d = await api.wallet()
    setData(d)
  }

  React.useEffect(() => { refresh().catch(()=>{}) }, [])

  async function tip() {
    setMsg(null)
    try {
      await api.tip(to, amount)
      setTo("")
      setMsg("Tip sent.")
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div style={{fontSize:18, fontWeight:700}}>Wallet</div>
          <span className="badge">credits (off-chain)</span>
        </div>

        <div className="item">
          <div className="muted small">Balance</div>
          <div style={{fontSize:26, fontWeight:800}}>{data?.wallet?.balance ?? "—"}</div>
        </div>

        <div className="item">
          <div style={{fontWeight:700, marginBottom:8}}>Tip a user</div>
          <div style={{display:"flex", gap:8}}>
            <input className="input" value={to} onChange={e=>setTo(e.target.value)} placeholder="@handle (without @)" />
            <input className="input" style={{maxWidth:140}} type="number" value={amount} onChange={e=>setAmount(Number(e.target.value))} />
            <button className="btn primary" onClick={tip} disabled={!to.trim() || amount<=0}>Tip</button>
          </div>
          {msg && <div className="muted small" style={{marginTop:6}}>{msg}</div>}
        </div>

        <div className="item">
          <div style={{fontWeight:700, marginBottom:8}}>Recent ledger (signed)</div>
          <div className="list">
            {(data?.ledger || []).map((t: any) => (
              <div className="item" key={t.id}>
                <div style={{display:"flex", justifyContent:"space-between"}}>
                  <div><span className="kbd">{t.reason}</span> <span className="muted small">amount</span> {t.amount}</div>
                  <div className="muted small">{new Date(t.created_at).toLocaleString()}</div>
                </div>
                <div className="muted small">from {t.from_wallet_id ?? "MINT"} → {t.to_wallet_id}</div>
                {t.signature && <div className="muted small">sig: {String(t.signature).slice(0, 18)}…</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:6}}>Rewards</div>
        <div className="muted small">
          • Starter grant on signup<br/>
          • Tips + bounties<br/>
          • Ledger tx are node-signed
        </div>
      </div>
    </div>
  )
}
