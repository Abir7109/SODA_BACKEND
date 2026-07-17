import { useState, useMemo, useCallback } from 'react'
import SlidePanel from '../SlidePanel'
import { Database, Table, Download, FileJson, BarChart3, ChevronDown, ChevronUp, Search, ArrowUpDown, Filter } from 'lucide-react'

function StatCard({ icon, label, value, color }) {
  return (
    <div className="agent-data-stat">
      <div className="agent-data-stat-icon" style={{ color: color || 'var(--accent)' }}>{icon}</div>
      <div>
        <div className="agent-data-stat-label">{label}</div>
        <div className="agent-data-stat-value">{value}</div>
      </div>
    </div>
  )
}

function MiniBarChart({ data, height }) {
  if (!data || data.length === 0) return null
  const vals = data.map(d => typeof d === 'number' ? d : 0)
  const max = Math.max(...vals, 1)
  return (
    <div className="agent-chart-mini" style={{ height: height || 50 }}>
      {vals.map((v, i) => (
        <div key={i} className="agent-chart-mini-bar-wrap">
          <div className="agent-chart-mini-bar" style={{ height: `${(v / max) * 100}%` }} />
        </div>
      ))}
    </div>
  )
}

function DataTable({ rows, columns, search }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const numericColumns = useMemo(() => {
    if (rows.length === 0 || columns.length === 0) return new Set()
    const numCols = new Set()
    for (const col of columns) {
      const sample = rows.find(r => r[col] != null && r[col] !== '')
      if (sample != null && !isNaN(Number(sample[col]))) numCols.add(col)
    }
    return numCols
  }, [rows, columns])

  const chartData = useMemo(() => {
    if (rows.length < 2 || numericColumns.size === 0) return null
    const col = [...numericColumns][0]
    return rows.slice(0, 20).map(r => Number(r[col]) || 0)
  }, [rows, numericColumns])

  const sorted = useMemo(() => {
    let list = [...rows]
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(r => Object.values(r).some(v => String(v || '').toLowerCase().includes(q)))
    }
    if (sortCol) {
      list.sort((a, b) => {
        const av = a[sortCol], bv = b[sortCol]
        if (av == null) return 1; if (bv == null) return -1
        const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv))
        return sortDir === 'asc' ? cmp : -cmp
      })
    }
    return list
  }, [rows, sortCol, sortDir, search])

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('asc') }
  }

  if (!rows || rows.length === 0 || !columns || columns.length === 0) return null

  return (
    <div>
      {chartData && chartData.length > 2 && (
        <div className="agent-chart-section">
          <div className="agent-chart-section-label">
            <BarChart3 size={10} />
            Data Preview: {[...numericColumns][0]}
          </div>
          <MiniBarChart data={chartData} height={60} />
        </div>
      )}

      <div className="agent-data-table-wrap">
        <table className="agent-data-table">
          <thead>
            <tr>
              {columns.map((col, i) => (
                <th key={i} onClick={() => handleSort(col)} style={{ cursor: 'pointer' }}>
                  <span className="agent-data-th-inner">
                    {col}
                    {sortCol === col && <ArrowUpDown size={9} style={{ transform: sortDir === 'asc' ? 'rotate(0deg)' : 'rotate(180deg)' }} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, 50).map((row, i) => (
              <tr key={i}>
                {columns.map((col, j) => {
                  const val = row[col]
                  const isNum = numericColumns.has(col)
                  return (
                    <td key={j} style={isNum ? { textAlign: 'right', fontFamily: "'JetBrains Mono', monospace" } : {}}>
                      {val != null ? (isNum ? Number(val).toLocaleString() : String(val)) : ''}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length > 50 && (
          <div className="agent-data-truncate">Showing 50 of {sorted.length} rows (filtered from {rows.length})</div>
        )}
        {sorted.length === 0 && search && (
          <div className="agent-empty">No results matching "{search}"</div>
        )}
      </div>
    </div>
  )
}

export default function DataPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(false)

  const result = d.result || ''
  const taskLabel = d.task || 'processed'
  const format = d.format || 'json'

  let displayType = 'text'
  let tableProps = { rows: [], columns: [] }
  let objectData = null
  let textResult = String(result)

  try {
    const parsed = typeof result === 'string' && (result.startsWith('[') || result.startsWith('{')) ? JSON.parse(result) : (typeof result === 'object' ? result : null)
    if (parsed) {
      if (Array.isArray(parsed)) {
        displayType = 'table'
        tableProps = { rows: parsed, columns: parsed.length > 0 ? Object.keys(parsed[0]) : [] }
      } else if (parsed.rows || parsed.data) {
        displayType = 'table'
        const rows = parsed.rows || parsed.data || []
        tableProps = { rows, columns: parsed.columns || (rows.length > 0 ? Object.keys(rows[0]) : []) }
      } else {
        displayType = 'object'
        objectData = parsed
        textResult = JSON.stringify(parsed, null, 2)
      }
    }
  } catch { textResult = String(result) }

  const handleExportCSV = useCallback(() => {
    if (tableProps.rows.length === 0) return
    const headers = tableProps.columns.join(',')
    const csvRows = tableProps.rows.map(r => tableProps.columns.map(c => {
      const v = r[c]; const s = String(v ?? '')
      return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
    }).join(','))
    const csv = [headers, ...csvRows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'data_export.csv'; a.click()
    URL.revokeObjectURL(url)
  }, [tableProps])

  return (
    <SlidePanel visible={visible} direction="bottom" title="DATA" icon={<Database size={11} />} accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
      <div className="agent-data-hero">
        <div className="agent-data-hero-icon"><BarChart3 size={20} /></div>
        <div>
          <div className="agent-data-hero-title">{taskLabel.toUpperCase()}</div>
          <div className="agent-data-hero-sub">{format.toUpperCase()} · {displayType.toUpperCase()}</div>
        </div>
      </div>

      <div className="agent-stats-row">
        <StatCard icon={<Table size={14} />} label="TYPE" value={displayType} color="#00fbfb" />
        {tableProps.rows.length > 0 && <StatCard icon={<Database size={14} />} label="ROWS" value={tableProps.rows.length.toLocaleString()} color="#22c55e" />}
        {tableProps.columns.length > 0 && <StatCard icon={<Filter size={14} />} label="COLS" value={tableProps.columns.length} color="#a78bfa" />}
        <StatCard icon={<FileJson size={14} />} label="FORMAT" value={format} color="#f59e0b" />
      </div>

      <div className="agent-divider" />

      {displayType === 'table' && tableProps.rows.length > 0 && (
        <>
          <div className="agent-data-search-bar">
            <Search size={10} />
            <input className="agent-data-search-input" placeholder="Filter rows..." value={search} onChange={e => setSearch(e.target.value)} />
            {tableProps.rows.length > 0 && (
              <button className="agent-code-tool-btn" onClick={handleExportCSV} title="Export CSV">
                <Download size={10} />
              </button>
            )}
          </div>
          <DataTable rows={tableProps.rows} columns={tableProps.columns} search={search} />
        </>
      )}

      {displayType !== 'table' && textResult && (
        <div className="agent-data-text-wrap">
          <pre className={expanded ? '' : 'agent-data-collapsed'}>{textResult}</pre>
          {textResult.length > 2000 && (
            <button className="agent-expand-btn" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? 'Collapse' : `Show all (${textResult.length.toLocaleString()} chars)`}
            </button>
          )}
        </div>
      )}

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
