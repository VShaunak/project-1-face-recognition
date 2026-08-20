import { useEffect, useState } from 'react'
import axios from 'axios'
import { Download } from 'lucide-react'

interface AttendanceRecord {
  id: number
  user_id: number
  check_in_time: string
  check_out_time: string | null
  confidence: number
  status: string
}

export default function AttendanceHistory() {
  const [records, setRecords] = useState<AttendanceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  useEffect(() => {
    fetchAttendance()
  }, [selectedDate])

  const fetchAttendance = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/attendance?date=${selectedDate}`)
      setRecords(response.data)
    } catch (error) {
      console.error('Failed to fetch attendance:', error)
    } finally {
      setLoading(false)
    }
  }

  const exportCSV = async () => {
    try {
      const response = await axios.get('http://localhost:8000/attendance/export/csv')
      const element = document.createElement('a')
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(response.data.data))
      element.setAttribute('download', response.data.filename)
      element.style.display = 'none'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Attendance History</h1>
        <button onClick={exportCSV} className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg">
          <Download size={20} />
          <span>Export CSV</span>
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Select Date</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">User ID</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Check-in Time</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Check-out Time</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Confidence</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : records.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-gray-500">No attendance records</td></tr>
            ) : (
              records.map((record) => (
                <tr key={record.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">{record.user_id}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{new Date(record.check_in_time).toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{record.check_out_time ? new Date(record.check_out_time).toLocaleString() : '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">{record.confidence.toFixed(1)}%</td>
                  <td className="px-6 py-4"><span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">{record.status}</span></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
