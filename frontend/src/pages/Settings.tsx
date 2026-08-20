export default function Settings() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>
      <div className="grid grid-cols-1 max-w-2xl gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">System Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Attendance Cooldown (hours)</label>
              <input type="number" defaultValue="4" className="w-full px-4 py-2 border border-gray-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Confidence Threshold (%)</label>
              <input type="number" defaultValue="60" min="0" max="100" className="w-full px-4 py-2 border border-gray-300 rounded-lg" />
            </div>
            <div>
              <label className="flex items-center space-x-2">
                <input type="checkbox" defaultChecked className="w-4 h-4" />
                <span className="text-gray-700">Enable Anti-Spoofing</span>
              </label>
            </div>
            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-lg">
              Save Settings
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">About</h2>
          <p className="text-gray-600">Face Recognition + Attendance System v1.0.0</p>
          <p className="text-gray-600 mt-2">Real-time face recognition and automated attendance tracking</p>
        </div>
      </div>
    </div>
  )
}
