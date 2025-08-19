import React, { useState } from 'react'

export default function Login({onSuccess}){
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [err, setErr] = useState(null)

  const submit = (e) => {
    e.preventDefault()
    if(user === 'admin' && pass === 'admin'){
      localStorage.setItem('auth', JSON.stringify({u:'admin'}))
      setErr(null)
      onSuccess && onSuccess()
    } else {
      setErr('Usuario o contraseña inválidos')
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-neutral-100">
      <form onSubmit={submit} className="card w-[360px]">
        <div className="text-lg font-semibold mb-4">Ingreso al sistema</div>
        <div className="space-y-3">
          <div className="space-y-1">
            <label className="block text-sm">Usuario</label>
            <input autoFocus value={user} onChange={e=>setUser(e.target.value)} className="border rounded px-2 py-2 w-full" placeholder="admin" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm">Contraseña</label>
            <input type="password" value={pass} onChange={e=>setPass(e.target.value)} className="border rounded px-2 py-2 w-full" placeholder="admin" />
          </div>
          {err && <div className="text-red-600 text-sm">{err}</div>}
          <button type="submit" className="w-full py-2 rounded bg-neutral-900 text-white">Ingresar</button>
          <div className="text-xs text-neutral-500">usr: admin • pass: admin</div>
        </div>
      </form>
    </div>
  )
}
