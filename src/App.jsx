import React, { useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './components/Dashboard.jsx'
import Parameters from './components/Parameters.jsx'
import PlcDiag from './components/PlcDiag.jsx'
import Logs from './components/Logs.jsx'
import Login from './components/Login.jsx'
import ArnegApp from './components/ArnegApp.jsx'
import PTZApp from './components/PTZApp.jsx'

export default function App(){
  const [route, setRoute] = useState('/')
  const [auth, setAuth] = useState(null)

  useEffect(() => {
    try{
      const a = JSON.parse(localStorage.getItem('auth') || 'null')
      setAuth(a)
    }catch{}
  }, [])

  const onLogout = () => {
    localStorage.removeItem('auth')
    setAuth(null)
  }

  const onLoginOk = () => {
    const a = JSON.parse(localStorage.getItem('auth') || 'null')
    setAuth(a)
  }

  if(!auth){
    return <Login onSuccess={onLoginOk} />
  }

  const render = () => {
    if(route === '/') return <Dashboard />
    if(route === '/parameters') return <Parameters />
    if(route === '/plc') return <PlcDiag />
    if(route === '/logs') return <Logs />
    if(route === '/arneg') return <ArnegApp />
    if(route === '/ptz') return <PTZApp />
    return <div className="p-4">Pantalla en construcción</div>
  }

  return (
    <div className="min-h-screen grid grid-cols-[260px_1fr] grid-rows-[64px_1fr]">
      <Header onLogout={onLogout} user={auth?.u} />
      <Sidebar route={route} onNavigate={setRoute} />
      <main className="p-4 col-start-2 row-start-2">
        {render()}
      </main>
    </div>
  )
}
