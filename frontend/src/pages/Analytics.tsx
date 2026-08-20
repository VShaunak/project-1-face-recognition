import { useEffect, useState } from 'react'
import axios from 'axios'

export default function Analytics() {
  const [analytics, setAnalytics] = useState<any>(null)

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get('http://localhost:8000/analytics/dashboard')
      setAnalytics(response.data)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    }
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Analytics</h1>

      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Weekly Attendance</h2>
            {analytics.weekly_attendance.length > 0 ? (
              <div className="space-y-2">
                {analytics.weekly_attendance.map((day: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-gray-600">{day.date}</span>
                    <span className="font-semibold text-blue-600">{day.count} users</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Department Distribution</h2>
            {analytics.department_distribution.length > 0 ? (
              <div className="space-y-2">
                {analytics.department_distribution.map((dept: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center">
                    <span className="text-gray-600">{dept.department}</span>
                    <span className="font-semibold text-green-600">{dept.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6 md:col-span-2">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Top Attendees</h2>
            {analytics.top_attendees.length > 0 ? (
              <table className="w-full">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2 text-gray-600">Name</th>
                    <th className="text-left py-2 text-gray-600">Department</th>
                    <th className="text-right py-2 text-gray-600">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.top_attendees.map((attendee: any, idx: number) => (
                    <tr key={idx} className="border-b hover:bg-gray-50">
                      <td className="py-3 text-gray-900">{attendee.name}</td>
                      <td className="py-3 text-gray-600">{attendee.department}</td>
                      <td className="py-3 text-right font-semibold text-blue-600">{attendee.attendance_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
