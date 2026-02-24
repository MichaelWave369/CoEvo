import React from "react"
import { Link, useNavigate } from "react-router-dom"
import { setToken, api, connectEvents } from "../api"
import { MeContext, Me, Notif } from "./MeContext"

export default function Layout({ children }: { children: React.ReactNode }) {
  const nav = useNavigate()
  const [me, setMe] = React.useState<Me>(null)
  const [unread, setUnread] = React.useState(0)
  const [notifs, setNotifs] = React.useState<Notif[]>([])
  const [open, setOpen] = React.useState(false)
  const [inviteLink, setInviteLink] = React.useState<string>("")

  async function refreshNotifs() {
    try {
      const c = await api.unreadCount()
      setUnread(c.count || 0)
      const list = await api.notifications(25)
      setNotifs(list)
    } catch {}
  }

  React.useEffect(() => {
    api.me().then(async (m)=>{ setMe(m); refreshNotifs(); try { const inv = await api.myInvite(); setInviteLink(inv.invite_link || "") } catch {} }).catch(() => setMe(null))
  }, [])

  React.useEffect(() => {
    if (!me) return
    const disconnect = connectEvents((ev) => {
      if (ev?.type === "notify" && ev.user_id === me.id) {
        setUnread(u => u + 1)
        setNotifs(prev => [ev.notification, ...prev].slice(0, 25))
      }
    })
    return () => disconnect()
  }, [me?.id])

  function logout() {
    setToken(null)
    setMe(null)
    nav("/login")
  }

  async function markRead(id: number) {
    try {
      await api.markRead(id)
      setNotifs(prev => prev.map(n => n.id === id ? {...n, read_at: new Date().toISOString()} : n))
      setUnread(u => Math.max(0, u-1))
    } catch {}
  }

  return (
    <MeContext.Provider value={{me, setMe, unread, setUnread, notifs, setNotifs}}>
      <div className="container">
        <div className="hdr">
          <div style={{display:"flex", gap:12, alignItems:"center"}}>
            <Link to="/" style={{fontSize:20, fontWeight:700}}>CoEvo</Link>
            <span className="badge">v0.4</span>
          </div>

          <div style={{display:"flex", gap:8, alignItems:"center"}}>
            {me ? (
              <>
                <div className="pop">
                  <button className={"btn " + (unread ? "ok" : "")} onClick={()=>{ setOpen(!open); if(!open) refreshNotifs() }}>
                    🔔 {unread ? unread : ""}
                  </button>
                  {open && (
                    <div className="popPanel">
                      <div className="hdr" style={{marginBottom:8}}>
                        <div style={{fontWeight:800}}>Notifications</div>
                        <button className="btn" onClick={()=>setOpen(false)}>X</button>
                      </div>
                      <div className="list">
                        {notifs.map(n => (
                          <div className="item" key={n.id} style={{opacity: n.read_at ? 0.65 : 1}}>
                            <div style={{display:"flex", justifyContent:"space-between", gap:10}}>
                              <div className="muted small">{new Date(n.created_at).toLocaleString()}</div>
                              {!n.read_at && <button className="btn" onClick={()=>markRead(n.id)}>Mark read</button>}
                            </div>
                            {n.thread_id && (
                              <div style={{marginTop:6}}>
                                <Link to={`/threads/${n.thread_id}`} onClick={()=>setOpen(false)}>
                                  Thread #{n.thread_id} updated
                                </Link>
                              </div>
                            )}
                            <div className="muted small">type: {n.event_type}</div>
                          </div>
                        ))}
                        {notifs.length === 0 && <div className="muted small">No notifications.</div>}
                      </div>
                    </div>
                  )}
                </div>

                <span className="muted small">as</span>
                <span className="kbd">@{me.handle}</span>
                {me.role !== "user" && <span className="badge">{me.role}</span>}
                <button className="btn" onClick={() => nav("/boards")}>Boards</button>
                <button className="btn" onClick={() => nav("/wallet")}>Wallet</button>
                <button className="btn" onClick={() => nav("/artifacts")}>Artifacts</button>
                <button className="btn" onClick={() => nav("/repos")}>Repos</button>
                <button className="btn" onClick={() => nav("/bounties")}>Bounties</button>
                <button className="btn" onClick={() => nav("/agents")}>Agents</button>
                <button className="btn" onClick={() => nav("/pulse")}>Pulse</button>
                <button className="btn" onClick={() => nav("/system")}>System</button>
                <button className="btn" onClick={() => inviteLink && navigator.clipboard.writeText(window.location.origin + inviteLink)}>Copy Invite</button>
                <button className="btn danger" onClick={logout}>Logout</button>
              </>
            ) : (
              <button className="btn primary" onClick={() => nav("/login")}>Login</button>
            )}
          </div>
        </div>

        {children}

        <div className="muted small" style={{marginTop:14}}>
          Tip: In <span className="kbd">help</span>, mention <span className="kbd">@sage</span>, <span className="kbd">@nova</span>, <span className="kbd">@forge</span>, or <span className="kbd">@echo</span> (enable with <span className="kbd">COEVO_AGENT_ENABLED=1</span>).
        </div>
      </div>
    </MeContext.Provider>
  )
}
