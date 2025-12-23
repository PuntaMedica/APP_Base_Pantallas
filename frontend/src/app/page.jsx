// page.jsx
'use client'

import React, { useState, useEffect } from 'react'

export default function Home() {
  // --- autenticación solo front ---
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser]             = useState('')
  const [password, setPassword]     = useState('')

  // --- datos del directorio ---
  const [cols, setCols]               = useState([])
  const [rows, setRows]               = useState([])
  const [originalCols, setOriginalCols] = useState([])
  const [originalRows, setOriginalRows] = useState([])
  const [textFilters, setTextFilters]   = useState([])
  const [selectFilters, setSelectFilters] = useState([])
  const [history, setHistory]           = useState([])

  useEffect(() => {
    if (localStorage.getItem('isLoggedIn') === 'true') {
      setIsLoggedIn(true)
      loadData()
    }
  }, [])

  // Carga datos del backend (público)
  const loadData = () => {
    fetch('/api/data')
      .then(r => {
        if (!r.ok) throw new Error('Error cargando datos')
        return r.json()
      })
      .then(d => {
        setCols(d.columns)
        setRows(d.rows)
        setOriginalCols(d.columns)
        setOriginalRows(d.rows)
        setTextFilters(Array(d.columns.length).fill(''))
        setSelectFilters(Array(d.columns.length).fill(''))
        setHistory([])
      })
      .catch(err => alert(err.message))
  }

  // Login front-end usando almacenamiento local
  const handleLogin = () => {
    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user, password })
    })
      .then(res => {
        if (!res.ok) throw new Error('Credenciales inválidas')
        return res.json()
      })
      .then(() => {
        localStorage.setItem('isLoggedIn', 'true')
        setIsLoggedIn(true)
        loadData()
      })
      .catch(err => alert(err.message))
  }

  // Logout front-end
  const handleLogout = () => {
    localStorage.removeItem('isLoggedIn')
    setIsLoggedIn(false)
    setUser('')
    setPassword('')
  }

  // Si no está logueado, mostrar formulario de login
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-6 rounded shadow-md w-full max-w-sm">
          <h2 className="text-2xl mb-4 text-center">Iniciar Sesión</h2>
          <input
            type="text"
            placeholder="Usuario"
            value={user}
            onChange={e => setUser(e.target.value)}
            className="w-full mb-3 px-3 py-2 border rounded focus:outline-none"
          />
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full mb-4 px-3 py-2 border rounded focus:outline-none"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-500 transition"
          >
            Entrar
          </button>
        </div>
      </div>
    )
  }

  // Funciones de historial y edición
  const pushHistory = () => {
    setHistory(h => [
      ...h,
      {
        cols: [...cols],
        rows: rows.map(r => [...r]),
        textFilters: [...textFilters],
        selectFilters: [...selectFilters]
      }
    ])
  }

  const undo = () => {
    if (!history.length) return
    const last = history[history.length - 1]
    setCols(last.cols)
    setRows(last.rows)
    setTextFilters(last.textFilters)
    setSelectFilters(last.selectFilters)
    setHistory(h => h.slice(0, -1))
  }

  const resetAll = () => {
    setCols(originalCols)
    setRows(originalRows)
    setTextFilters(Array(originalCols.length).fill(''))
    setSelectFilters(Array(originalCols.length).fill(''))
    setHistory([])
  }

  // Filtros de texto y selección
  const updateTextFilter = (i, v) => {
    const f = [...textFilters]; f[i] = v; setTextFilters(f)
  }
  const updateSelectFilter = (i, v) => {
    const f = [...selectFilters]; f[i] = v; setSelectFilters(f)
  }
  const clearFilters = () => {
    setTextFilters(Array(cols.length).fill(''))
    setSelectFilters(Array(cols.length).fill(''))
  }

  const filteredRows = rows.filter(row =>
    cols.every((_, i) => {
      const tf = textFilters[i].toLowerCase()
      const sf = selectFilters[i]
      const val = String(row[i]).toLowerCase()
      return val.includes(tf) && (sf === '' || String(row[i]) === sf)
    })
  )

  // Edición de celdas, filas y columnas
  const updateCell = (r, c, v) => {
    pushHistory()
    setRows(rows.map((row, i) => i === r
      ? row.map((cell, j) => j === c ? v : cell)
      : row
    ))
  }

  const addRow = () => {
    pushHistory()
    setRows([...rows, Array(cols.length).fill('')])
  }
  const delRow = i => {
    if (!confirm('¿Seguro que deseas eliminar esta fila?')) return
    pushHistory()
    setRows(rows.filter((_, idx) => idx !== i))
  }

  const addCol = () => {
    pushHistory()
    setCols([...cols, 'Nueva columna'])
    setRows(rows.map(r => [...r, '']))
    setTextFilters([...textFilters, ''])
    setSelectFilters([...selectFilters, ''])
  }
  const delCol = j => {
    if (!confirm(`¿Seguro que deseas eliminar la columna "${cols[j]}"?`)) return
    pushHistory()
    setCols(cols.filter((_, idx) => idx !== j))
    setRows(rows.map(r => r.filter((_, idx) => idx !== j)))
    setTextFilters(textFilters.filter((_, idx) => idx !== j))
    setSelectFilters(selectFilters.filter((_, idx) => idx !== j))
  }

  // Subida de fotos
  const handlePhotoUpload = (rowIdx, file) => {
    const form = new FormData()
    form.append('photo', file)
    const fnIdx = cols.indexOf('Nombre')
    const ppIdx = cols.indexOf('Apellido Paterno')
    const pmIdx = cols.indexOf('Apellido Materno')
    form.append('firstName', rows[rowIdx][fnIdx] || '')
    form.append('paterno',   rows[rowIdx][ppIdx] || '')
    form.append('materno',   rows[rowIdx][pmIdx] || '')

    fetch('/api/upload-photo', {
      method: 'POST',
      body: form
    })
      .then(r => r.json())
      .then(({ filename }) => {
        if (filename) updateCell(rowIdx, cols.indexOf('Foto'), filename)
      })
  }

  // Descargar Excel
  const downloadExcel = () => {
    fetch('/api/download')
      .then(res => res.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'DIRECTORIO.xlsx'
        document.body.appendChild(a)
        a.click()
        a.remove()
      })
  }

  // Guardar cambios
  const save = () => {
    fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ columns: cols, rows })
    })
      .then(() => alert('Guardado exitoso'))
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-6xl mx-auto bg-white rounded-xl shadow-lg p-6 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-gray-700">Directorio en Excel</h1>
          <div className="space-x-2">
            <button onClick={downloadExcel} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-500">
              Descargar Excel
            </button>
            <button onClick={handleLogout} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-400">
              Cerrar Sesión
            </button>
          </div>
        </div>

        {/* Controles */}
        <div className="flex flex-wrap gap-2">
          <button onClick={addRow}   className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-400">+ Fila</button>
          <button onClick={addCol}   className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-400">+ Columna</button>
          <button onClick={undo}     className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-400">Revertir</button>
          <button onClick={resetAll} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-400">Cancelar todo</button>
          <button onClick={clearFilters} className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-400">Limpiar filtros</button>
        </div>

        {/* Tabla */}
        <div className="overflow-auto border rounded" style={{ height: '60vh' }}>
          <table className="w-full table-auto border-collapse">
            <thead>
              <tr>
                {cols.map((c, i) => (
                  <th key={i} className="sticky top-0 bg-blue-50 p-2 border z-20">
                    <div className="flex items-center space-x-1">
                      <input
                        value={c}
                        onChange={e => setCols(cols.map((x, j) => j === i ? e.target.value : x))}
                        className="flex-1 bg-white border rounded px-2 py-1 focus:ring-2 focus:ring-blue-300"
                      />
                      <button onClick={() => delCol(i)} className="text-red-500 hover:text-red-700">×</button>
                    </div>
                  </th>
                ))}
                <th className="sticky top-0 bg-blue-50 p-2 border z-20">Acción</th>
              </tr>
              <tr>
                {cols.map((_, i) => {
                  const opts = Array.from(new Set(rows.map(r => String(r[i]))))
                  return (
                    <th key={i} className="sticky top-12 bg-blue-50 p-2 border z-20">
                      <div className="flex flex-col space-y-1">
                        <input
                          value={textFilters[i]}
                          onChange={e => updateTextFilter(i, e.target.value)}
                          placeholder="Filtrar…"
                          className="w-full bg-white border rounded px-2 py-1 text-sm focus:ring-2 focus:ring-blue-300"
                        />
                        <select
                          value={selectFilters[i]}
                          onChange={e => updateSelectFilter(i, e.target.value)}
                          className="w-full bg-white border rounded px-2 py-1 text-sm focus:ring-2 focus:ring-blue-300"
                        >
                          <option value="">Todos</option>
                          {opts.map((v, k) => (
                            <option key={k} value={v}>{v}</option>
                          ))}
                        </select>
                      </div>
                    </th>
                  )
                })}
                <th className="sticky top-12 bg-blue-50 p-2 border z-20"></th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, i) => {
                const realIndex = rows.indexOf(row)
                return (
                  <tr key={i} className="hover:bg-gray-50">
                    {row.map((cell, j) => (
                      <td key={j} className="p-2 border text-center">
                        {cols[j] === 'Activo' ? (
                          <div className="flex justify-center space-x-2">
                            <button onClick={() => updateCell(realIndex, j, '✓')} className={`px-2 py-1 rounded ${row[j] === '✓' ? 'bg-green-500 text-white' : 'bg-gray-200'}`}>✓</button>
                            <button onClick={() => updateCell(realIndex, j, '✗')} className={`px-2 py-1 rounded ${row[j] === '✗' ? 'bg-red-500 text-white' : 'bg-gray-200'}`}>✗</button>
                          </div>
                        ) : cols[j] === 'Foto' ? (
                          <div className="flex flex-col items-center space-y-1">
                            {cell
                              ? <span className="text-sm font-medium text-green-700">Ya hay foto</span>
                              : <span className="text-sm font-medium text-gray-500">Sin foto</span>
                            }
                            <label className="cursor-pointer px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-500 text-xs font-semibold">
                              {cell ? 'Cambiar foto' : 'Subir foto'}
                              <input
                                type="file"
                                accept="image/*"
                                onChange={e => handlePhotoUpload(realIndex, e.target.files[0])}
                                className="hidden"
                              />
                            </label>
                          </div>
                        ) : (
                          <input
                            value={cell}
                            onChange={e => updateCell(realIndex, j, e.target.value)}
                            className="w-full bg-transparent focus:outline-none"
                          />
                        )}
                      </td>
                    ))}
                    <td className="p-2 border text-center">
                      <button onClick={() => delRow(realIndex)} className="px-2 py-1 bg-red-500 text-white rounded hover:bg-red-400">
                        Eliminar Fila
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Guardar cambios */}
        <div className="text-right">
          <button onClick={save} className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-500">
            Guardar cambios
          </button>
        </div>
      </div>
    </div>
  )
}
