import React from "react"

type Props = {
  children: React.ReactNode
}

type State = {
  hasError: boolean
  message: string
}

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, message: "" }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error?.message || "Unknown UI error" }
  }

  componentDidCatch(error: Error) {
    console.error("UI crash caught by ErrorBoundary", error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card">
          <div style={{ fontSize: 18, fontWeight: 700 }}>Something went wrong</div>
          <div className="muted" style={{ marginTop: 8 }}>
            We hit a UI error while rendering this page.
          </div>
          <div className="item" style={{ marginTop: 10, borderColor: "var(--danger)", color: "var(--danger)" }}>
            {this.state.message}
          </div>
          <button className="btn" style={{ marginTop: 10 }} onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
