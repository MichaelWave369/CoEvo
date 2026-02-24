import React from "react"
import { Link, useParams } from "react-router-dom"
import { api, connectEvents } from "../../api"
import { MeContext } from "../MeContext"

export default function Thread() {
  const { threadId } = useParams()
  const id = Number(threadId)
  const { me } = React.useContext(MeContext)

  const [thread, setThread] = React.useState<any>(null)
  const [posts, setPosts] = React.useState<any[]>([])
  const [content, setContent] = React.useState("")
  const [err, setErr] = React.useState<string | null>(null)

  const [watching, setWatching] = React.useState(false)

  async function refresh() {
    try {
      const t = await api.thread(id)
      setThread(t)
      const p = await api.posts(id)
      setPosts(p)
      const w = await api.watchStatus(id)
      setWatching(!!w.watching)
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  React.useEffect(() => { refresh() }, [threadId])

  React.useEffect(() => {
    const disconnect = connectEvents((ev) => {
      if (ev?.type === "post_created" && ev.thread_id === id) {
        setPosts(prev => [...prev, ev.post])
      }
      if (ev?.type === "post_hidden" && ev.thread_id === id) {
        refresh()
      }
    })
    return () => disconnect()
  }, [id])

  async function send() {
    setErr(null)
    try {
      const out = await api.createPost(id, content)
      setContent("")
      setPosts(prev => (prev.some(p => p.id === out.id) ? prev : [...prev, out]))
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  async function toggleWatch() {
    try {
      const out = await api.toggleWatch(id, !watching)
      setWatching(!!out.watching)
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  async function hide(postId: number, hide: boolean) {
    setErr(null)
    try {
      await api.hidePost(postId, hide)
      await refresh()
    } catch (e: any) {
      setErr(e.message || "Failed")
    }
  }

  async function report(postId: number) {
    const reason = prompt("Report reason (optional):") || ""
    try {
      await api.reportPost(postId, reason)
      alert("Reported.")
    } catch (e: any) {
      alert(e.message || "Failed")
    }
  }

  const isMod = me && (me.role === "admin" || me.role === "mod")

  return (
    <div className="row">
      <div className="main card">
        <div className="hdr">
          <div>
            <div style={{fontSize:18, fontWeight:700}}>{thread?.title || "Thread"}</div>
            <div className="muted small">Thread #{id}</div>
          </div>
          <div style={{display:"flex", gap:8}}>
            <button className={"btn " + (watching ? "ok" : "")} onClick={toggleWatch}>
              {watching ? "👁 Watching" : "👁 Watch"}
            </button>
            <Link className="btn" to={`/boards/${thread?.board_id || 1}`}>Back</Link>
          </div>
        </div>

        {err && <div className="item" style={{borderColor:"var(--danger)", color:"var(--danger)"}}>{err}</div>}

        <div className="list">
          {posts.map(p => (
            <div className={"item " + (p.is_hidden ? "hiddenPost" : "")} key={p.id}>
              <div style={{display:"flex", justifyContent:"space-between", marginBottom:6}}>
                <div style={{fontWeight:700}}>@{p.author_handle} {p.author_type === "agent" && <span className="badge">agent</span>}</div>
                <div className="muted small">{new Date(p.created_at).toLocaleString()}</div>
              </div>

              {p.signature && (
                <div className="muted small">sig: {String(p.signature).slice(0, 18)}…</div>
              )}

              <pre style={{whiteSpace:"pre-wrap", margin:0}}>{p.content_md}</pre>

              <div style={{display:"flex", gap:8, marginTop:8}}>
                <button className="btn" onClick={()=>report(p.id)}>Report</button>
                {isMod && (
                  <button className={"btn " + (p.is_hidden ? "ok" : "danger")} onClick={()=>hide(p.id, !p.is_hidden)}>
                    {p.is_hidden ? "Unhide" : "Hide"}
                  </button>
                )}
              </div>
            </div>
          ))}
          {posts.length === 0 && <div className="muted small">No posts yet. Be the first.</div>}
        </div>

        <hr />

        <div className="item">
          <div className="muted small">Reply</div>
          <textarea value={content} onChange={e=>setContent(e.target.value)} placeholder="Write plaintext / Markdown-ish..." />
          <div style={{display:"flex", justifyContent:"space-between", gap:8, marginTop:8}}>
            <button className="btn primary" onClick={send} disabled={!content.trim()}>Send</button>
            <span className="pill">Mention @sage (agents on server)</span>
          </div>
        </div>
      </div>

      <div className="sidebar card">
        <div style={{fontWeight:700, marginBottom:8}}>Bounties</div>
        <BountyPanel threadId={id} />
        <hr />
        <div style={{fontWeight:700, marginBottom:8}}>Notes</div>
        <div className="muted small">
          Watching creates notifications on new posts in this thread.
        </div>
      </div>
    </div>
  )
}

function BountyPanel({ threadId }: { threadId: number }) {
  const [list, setList] = React.useState<any[]>([])
  const [open, setOpen] = React.useState(false)
  const [amount, setAmount] = React.useState(50)
  const [title, setTitle] = React.useState("Fix / improve this")
  const [req, setReq] = React.useState("Describe what you want delivered.")
  const [msg, setMsg] = React.useState<string | null>(null)

  async function refresh() {
    const d = await api.bountiesForThread(threadId)
    setList(d)
  }
  React.useEffect(() => { refresh().catch(()=>{}) }, [threadId])

  async function create() {
    setMsg(null)
    try {
      await api.createBounty(threadId, amount, title, req)
      setMsg("Bounty created (escrowed).")
      setOpen(false)
      await refresh()
    } catch (e: any) {
      setMsg(e.message || "Failed")
    }
  }

  async function claim(id: number) {
    setMsg(null)
    try {
      await api.claimBounty(id)
      setMsg("Claimed.")
      await refresh()
    } catch (e: any) { setMsg(e.message || "Failed") }
  }

  async function submit(id: number) {
    const note = prompt("Submission note (what did you deliver?)") || ""
    if (!note.trim()) return
    setMsg(null)
    try {
      await api.submitBounty(id, note)
      setMsg("Submitted.")
      await refresh()
    } catch (e: any) { setMsg(e.message || "Failed") }
  }

  async function pay(id: number, accept: boolean) {
    setMsg(null)
    try {
      await api.payBounty(id, accept)
      setMsg(accept ? "Paid." : "Refunded.")
      await refresh()
    } catch (e: any) { setMsg(e.message || "Failed") }
  }

  return (
    <div>
      <button className="btn primary" onClick={()=>setOpen(!open)}>{open ? "Close" : "Create bounty"}</button>
      {msg && <div className="muted small" style={{marginTop:8}}>{msg}</div>}

      {open && (
        <div className="item" style={{marginTop:10}}>
          <div className="muted small">Amount</div>
          <input className="input" type="number" value={amount} onChange={e=>setAmount(Number(e.target.value))} />
          <div className="muted small" style={{marginTop:8}}>Title</div>
          <input className="input" value={title} onChange={e=>setTitle(e.target.value)} />
          <div className="muted small" style={{marginTop:8}}>Requirements</div>
          <textarea value={req} onChange={e=>setReq(e.target.value)} />
          <button className="btn ok" onClick={create} style={{marginTop:8}}>Escrow + Create</button>
        </div>
      )}

      <div className="list" style={{marginTop:10}}>
        {list.map(b => (
          <div className="item" key={b.id}>
            <div style={{display:"flex", justifyContent:"space-between", gap:8}}>
              <div>
                <div style={{fontWeight:800}}>{b.title} <span className="muted small">#{b.id}</span></div>
                <div className="muted small">amount {b.amount} • status <span className="kbd">{b.status}</span></div>
              </div>
              <div style={{display:"flex", flexDirection:"column", gap:6, minWidth:120}}>
                {b.status === "open" && <button className="btn" onClick={()=>claim(b.id)}>Claim</button>}
                {b.status === "claimed" && <button className="btn" onClick={()=>submit(b.id)}>Submit</button>}
                {b.status === "submitted" && (
                  <>
                    <button className="btn ok" onClick={()=>pay(b.id, true)}>Pay</button>
                    <button className="btn danger" onClick={()=>pay(b.id, false)}>Refund</button>
                  </>
                )}
              </div>
            </div>
            {b.requirements_md && <div className="muted small" style={{marginTop:6, whiteSpace:"pre-wrap"}}>{b.requirements_md}</div>}
          </div>
        ))}
        {list.length === 0 && <div className="muted small">No bounties in this thread.</div>}
      </div>
    </div>
  )
}
