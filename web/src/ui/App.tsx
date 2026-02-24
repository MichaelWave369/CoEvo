import React from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import Layout from "./Layout"
import ErrorBoundary from "./ErrorBoundary"
import Login from "./pages/Login"
import Boards from "./pages/Boards"
import Landing from "./pages/Landing"
import Profile from "./pages/Profile"
import Votes from "./pages/Votes"
import Welcome from "./pages/Welcome"
import Board from "./pages/Board"
import Thread from "./pages/Thread"
import Wallet from "./pages/Wallet"
import Artifacts from "./pages/Artifacts"
import Repos from "./pages/Repos"
import Bounties from "./pages/Bounties"
import System from "./pages/System"
import Agents from "./pages/Agents"
import Pulse from "./pages/Pulse"

export default function App() {
  return (
    <Layout>
      <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/boards" element={<Boards />} />
        <Route path="/login" element={<Login />} />
        <Route path="/welcome" element={<Welcome />} />
        <Route path="/boards/:boardId" element={<Board />} />
        <Route path="/threads/:threadId" element={<Thread />} />
        <Route path="/wallet" element={<Wallet />} />
        <Route path="/artifacts" element={<Artifacts />} />
        <Route path="/repos" element={<Repos />} />
        <Route path="/bounties" element={<Bounties />} />
        <Route path="/system" element={<System />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/pulse" element={<Pulse />} />
        <Route path="/profile/:kind/:handle" element={<Profile />} />
        <Route path="/votes" element={<Votes />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </ErrorBoundary>
    </Layout>
  )
}
