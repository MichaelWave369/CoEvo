const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") || ""

function buildUrl(path: string): string {
  if (!API_BASE) return path
  return `${API_BASE}${path}`
}

export function getToken(): string | null {
  return localStorage.getItem("coevo_token")
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem("coevo_token", t)
  else localStorage.removeItem("coevo_token")
}

async function request(path: string, opts: RequestInit = {}) {
  const token = getToken()
  const headers: Record<string, string> = { ...(opts.headers as any) }
  if (!(opts.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json"
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(buildUrl(path), { ...opts, headers })
  const text = await res.text()
  let data: any = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) {
    const msg = typeof data === "string" ? data : (data?.detail || "Request failed")
    throw new Error(msg)
  }
  return data
}

export const api = {
  health: () => request("/api/health"),

  register: (handle: string, password: string, email?: string) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ handle, password, email }) }),

  login: async (handle: string, password: string) => {
    const out = await request("/api/auth/login", { method: "POST", body: JSON.stringify({ handle, password }) })
    setToken(out.access_token)
    return out
  },

  me: () => request("/api/me"),

  boards: () => request("/api/boards"),
  toggleSub: (boardId: number, subscribe: boolean) =>
    request(`/api/subscriptions/boards/${boardId}`, { method: "POST", body: JSON.stringify({ subscribe }) }),

  threads: (boardId: number) => request(`/api/boards/${boardId}/threads`),
  createThread: (boardId: number, title: string) =>
    request(`/api/boards/${boardId}/threads`, { method: "POST", body: JSON.stringify({ title }) }),

  thread: (threadId: number) => request(`/api/threads/${threadId}`),
  posts: (threadId: number) => request(`/api/threads/${threadId}/posts`),
  createPost: (threadId: number, content_md: string) =>
    request(`/api/threads/${threadId}/posts`, { method: "POST", body: JSON.stringify({ content_md }) }),

  hidePost: (postId: number, hide: boolean) =>
    request(`/api/mod/posts/${postId}/hide`, { method: "POST", body: JSON.stringify({ hide }) }),

  reportPost: (postId: number, reason: string) =>
    request(`/api/mod/posts/${postId}/report`, { method: "POST", body: JSON.stringify({ reason }) }),

  artifacts: () => request("/api/artifacts"),
  uploadArtifact: (file: File) => {
    const fd = new FormData()
    fd.append("file", file)
    return request("/api/artifacts/upload", { method: "POST", body: fd, headers: {} as any })
  },
  downloadArtifactUrl: (id: number) => buildUrl(`/api/artifacts/${id}/download`),

  repos: () => request("/api/repos"),
  addRepo: (url: string, title: string, description: string, tags: string[]) =>
    request("/api/repos", { method: "POST", body: JSON.stringify({ url, title, description, tags }) }),

  wallet: () => request("/api/wallet"),
  tip: (to_handle: string, amount: number) =>
    request("/api/wallet/tip", { method: "POST", body: JSON.stringify({ to_handle, amount }) }),

  bounties: () => request("/api/bounties"),
  bountiesForThread: (threadId: number) => request(`/api/bounties/thread/${threadId}`),
  createBounty: (threadId: number, amount: number, title: string, requirements_md: string) =>
    request(`/api/bounties/thread/${threadId}`, { method: "POST", body: JSON.stringify({ amount, title, requirements_md }) }),
  claimBounty: (id: number) => request(`/api/bounties/${id}/claim`, { method: "POST", body: JSON.stringify({}) }),
  submitBounty: (id: number, note_md: string) =>
    request(`/api/bounties/${id}/submit`, { method: "POST", body: JSON.stringify({ note_md }) }),
  payBounty: (id: number, accept: boolean) =>
    request(`/api/bounties/${id}/pay`, { method: "POST", body: JSON.stringify({ accept }) }),

  watchStatus: (threadId: number) => request(`/api/watches/thread/${threadId}`),
  toggleWatch: (threadId: number, watch: boolean) => request(`/api/watches/thread/${threadId}`, { method: "POST", body: JSON.stringify({ watch }) }),

  notifications: (limit=30) => request(`/api/notifications?limit=${limit}`),
  unreadCount: () => request(`/api/notifications/unread-count`),
  markRead: (id: number) => request(`/api/notifications/${id}/read`, { method: "PATCH", body: JSON.stringify({ read: true }) }),

  publicKey: () => request("/api/system/public-key"),
  auditExportUrl: () => buildUrl(`/api/audit/export`)
}

export function connectEvents(onMessage: (ev: any) => void) {
  const es = new EventSource(buildUrl(`/api/events`))
  es.addEventListener("message", (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data)
      onMessage(data)
    } catch {}
  })
  es.onerror = () => {}
  return () => es.close()
}
