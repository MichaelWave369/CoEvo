import React from "react"

export type Me = { id: number, handle: string, role: string } | null

export type Notif = {
  id: number
  thread_id: number | null
  event_type: string
  payload: any
  created_at: string
  read_at: string | null
}

export const MeContext = React.createContext<{
  me: Me,
  setMe: (m: Me)=>void,
  unread: number,
  setUnread: (n:number)=>void,
  notifs: Notif[],
  setNotifs: (n: Notif[])=>void
}>({me:null,setMe:()=>{}, unread:0, setUnread:()=>{}, notifs:[], setNotifs:()=>{}})
