import React from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import Layout from "./Layout"
import Login from "./pages/Login"
import Boards from "./pages/Boards"
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
      <Routes>
        <Route path="/" element={<Boards />} />
        <Route path="/login" element={<Login />} />
        <Route path="/boards/:boardId" element={<Board />} />
        <Route path="/threads/:threadId" element={<Thread />} />
        <Route path="/wallet" element={<Wallet />} />
        <Route path="/artifacts" element={<Artifacts />} />
        <Route path="/repos" element={<Repos />} />
        <Route path="/bounties" element={<Bounties />} />
        <Route path="/system" element={<System />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/pulse" element={<Pulse />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
