const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

async function jget(path){
  const r = await fetch(API_BASE + path)
  if(!r.ok) throw new Error(`${r.status}`)
  return await r.json()
}

async function jpost(path, body){
  const r = await fetch(API_BASE + path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body||{})
  })
  if(!r.ok) throw new Error(`${r.status}`)
  return await r.json()
}

export function useHealth(){
  return {
    fetch: () => jget('/health')
  }
}

export function usePlc(){
  return {
    ping: () => jget('/plc/ping'),
    read: (db, start, size) => jget(`/plc/db/${db}/read?start=${start}&size=${size}`),
    write: (db, start, data_b64) => jpost(`/plc/db/${db}/write`, {start, data_b64})
  }
}

export function useParameters(){
  return {
    list: () => jget('/parameters/'),
    get: (key) => jget(`/parameters/${key}`),
    upsert: (key, value) => jpost('/parameters/', {key, value})
  }
}
