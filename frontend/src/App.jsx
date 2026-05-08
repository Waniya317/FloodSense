import { useState } from 'react'
import './App.css'

function App() {
  const [formData, setFormData] = useState({
    district: '',
    precipitation: '',
    temperature: '',
    humidity: '',
    wind_speed: '',
    soil_moisture: '',
    water_area_km2: '0',
    month: new Date().getMonth() + 1,
    is_monsoon: 0,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const API_BASE = 'http://localhost:8000/api/v1'
  
  // Valid district names from the dataset
  const VALID_DISTRICTS = [
    'buner', 'swat', 'nowshera', 'charsadda', 'peshawar', 'mardan',
    'dera ismail khan', 'dera ghazi khan', 'rajanpur', 'muzaffargarh',
    'jacobabad', 'larkana', 'sukkur', 'abbottabad', 'mansehra'
  ]

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: (name === 'month' || name === 'is_monsoon' || name === 'water_area_km2') ? parseFloat(value) : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      if (!formData.district.trim()) {
        throw new Error('Please select a district')
      }

      if (!VALID_DISTRICTS.includes(formData.district.toLowerCase())) {
        throw new Error('Invalid district selected')
      }

      const payload = {
        district: formData.district.trim(),
        precipitation: formData.precipitation ? parseFloat(formData.precipitation) : null,
        temperature: formData.temperature ? parseFloat(formData.temperature) : null,
        humidity: formData.humidity ? parseFloat(formData.humidity) : null,
        wind_speed: formData.wind_speed ? parseFloat(formData.wind_speed) : null,
        soil_moisture: formData.soil_moisture ? parseFloat(formData.soil_moisture) : null,
        water_area_km2: formData.water_area_km2 ? parseFloat(formData.water_area_km2) : null,
        month: formData.month,
        is_monsoon: formData.is_monsoon,
      }

      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Prediction failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getRiskLevel = (probability) => {
    if (probability < 0.25) return { level: 'LOW', urdu: 'کم', color: '#10b981', icon: '✓' }
    if (probability < 0.50) return { level: 'MEDIUM', urdu: 'متوسط', color: '#f59e0b', icon: '⚠' }
    if (probability < 0.75) return { level: 'HIGH', urdu: 'زیادہ', color: '#ef4444', icon: '⛔' }
    return { level: 'CRITICAL', urdu: 'انتہائی', color: '#7c3aed', icon: '‼' }
  }

  // Check if alert mode should be active
  const isAlertMode = result && (result.prediction?.risk_level === 'High' || result.prediction?.risk_level === 'Critical')

  return (
    <div className="app-container">
      {/* Alert Mode Banner - Only shows for High/Critical risk */}
      {isAlertMode && (
        <div className="alert-banner">
          <div className="alert-content">
            <div className="alert-icon">🚨</div>
            <div className="alert-text">
              <h3>RIVER ALERT INCOMING</h3>
              <h4 style={{ fontSize: '1rem', margin: '0.25rem 0', fontWeight: '600', color: '#fff' }}>
                دریا میں سیلاب کا خطرہ
              </h4>
              <p className="alert-action">
                {result.recommendation?.immediate_actions?.[0] ||
                  result.recommendation?.summary_en ||
                  "Immediate action required - contact PDMA"}
              </p>
            </div>
            <div className="alert-district">
              <strong>{result.district?.toUpperCase()}</strong>
            </div>
          </div>
        </div>
      )}

      <header className="app-header">
        <div className="header-content">
          <h1>🌊 FloodSense AI</h1>
          <p>Advanced Flood Risk Prediction System</p>
        </div>
      </header>

      {/* Data Estimation Info Box */}
      <div className="info-box">
        <div className="info-content">
          <p className="info-text-en">
            <strong>Note:</strong> Missing rainfall data was estimated using geographically nearest districts based on latitude and longitude coordinates to ensure accurate and location-aware flood predictions.
          </p>
          <p className="info-text-ur">
            <strong>نوٹ:</strong> بارش کا غائب ڈیٹا عرض البلد اور طول البلد کی بنیاد پر جغرافیائی طور پر قریبی اضلاع سے اندازہ لگا کر مکمل کیا گیا تاکہ درست اور مقام سے متعلق سیلاب کی پیشگوئی ممکن ہو سکے۔
          </p>
        </div>
      </div>

      <main className="app-main">
        <div className="grid-container">
          {/* Form Section */}
          <div className="form-section">
            <h2>📊 Prediction Input</h2>
            <form onSubmit={handleSubmit} className="prediction-form">
              {/* District Input - Required */}
              <div className="form-group required">
                <label htmlFor="district">District Name</label>
                <select
                  id="district"
                  name="district"
                  value={formData.district}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">Select a district...</option>
                  {VALID_DISTRICTS.map(district => (
                    <option key={district} value={district}>
                      {district.charAt(0).toUpperCase() + district.slice(1).replace(' ', ' ')}
                    </option>
                  ))}
                </select>
                <small>Select from the list of supported districts</small>
              </div>

              {/* Weather Parameters */}
              <div className="form-divider">Weather Parameters</div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="precipitation">Precipitation (mm)</label>
                  <input
                    type="number"
                    id="precipitation"
                    name="precipitation"
                    value={formData.precipitation}
                    onChange={handleInputChange}
                    placeholder="0-3000"
                    min="0"
                    max="3000"
                    step="0.1"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="temperature">Temperature (°C)</label>
                  <input
                    type="number"
                    id="temperature"
                    name="temperature"
                    value={formData.temperature}
                    onChange={handleInputChange}
                    placeholder="-20 to 60"
                    min="-20"
                    max="60"
                    step="0.1"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="humidity">Humidity (%)</label>
                  <input
                    type="number"
                    id="humidity"
                    name="humidity"
                    value={formData.humidity}
                    onChange={handleInputChange}
                    placeholder="0-100"
                    min="0"
                    max="100"
                    step="0.1"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="wind_speed">Wind Speed (km/h)</label>
                  <input
                    type="number"
                    id="wind_speed"
                    name="wind_speed"
                    value={formData.wind_speed}
                    onChange={handleInputChange}
                    placeholder="0-60"
                    min="0"
                    max="60"
                    step="0.1"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="soil_moisture">Soil Moisture (0-1)</label>
                  <input
                    type="number"
                    id="soil_moisture"
                    name="soil_moisture"
                    value={formData.soil_moisture}
                    onChange={handleInputChange}
                    placeholder="0-1"
                    min="0"
                    max="1"
                    step="0.01"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="water_area_km2">Visible Surface Water</label>
                  <select
                    id="water_area_km2"
                    name="water_area_km2"
                    value={formData.water_area_km2}
                    onChange={handleInputChange}
                  >
                    <option value="0">No</option>
                    <option value="12.3">Yes</option>
                  </select>
                </div>
              </div>

              {/* Temporal Parameters */}
              <div className="form-divider">Temporal Information</div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="month">Month</label>
                  <select
                    id="month"
                    name="month"
                    value={formData.month}
                    onChange={handleInputChange}
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="is_monsoon">Monsoon Season</label>
                  <select
                    id="is_monsoon"
                    name="is_monsoon"
                    value={formData.is_monsoon}
                    onChange={handleInputChange}
                  >
                    <option value={0}>No</option>
                    <option value={1}>Yes</option>
                  </select>
                </div>
              </div>

              {error && <div className="error-message">{error}</div>}

              <button
                type="submit"
                className="submit-btn"
                disabled={loading}
              >
                {loading ? '⏳ Predicting...' : '🔍 Predict Flood Risk'}
              </button>
            </form>
          </div>

          {/* Result Section */}
          <div className="result-section">
            {result ? (
              <div className="result-card">
                <h2>📈 Prediction Result</h2>

                {/* Risk Level Display */}
                <div className="risk-container">
                  {(() => {
                    const prob = result.prediction?.probability ?? 0
                    const risk = getRiskLevel(prob)
                    return (
                      <div className="risk-display" style={{ borderColor: risk.color }}>
                        <div className="risk-icon" style={{ color: risk.color }}>
                          {risk.icon}
                        </div>
                        <div className="risk-info">
                          <h3 style={{ color: risk.color }}>{result.prediction?.risk_level || risk.level} RISK</h3>
                          <h4 style={{ color: risk.color, fontSize: '1.1rem', margin: '0.25rem 0', fontWeight: '600' }}>
                            {result.prediction?.risk_level_urdu || risk.urdu} خطرہ
                          </h4>
                          <p className="risk-probability">
                            {(prob * 100).toFixed(1)}% Probability
                          </p>
                          <div className="risk-bar">
                            <div
                              className="risk-fill"
                              style={{
                                width: `${prob * 100}%`,
                                backgroundColor: risk.color,
                              }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    )
                  })()}
                </div>

                {/* District Info */}
                {result.district_info && (
                  <div className="info-card">
                    <h4>📍 District Information</h4>
                    <div className="info-grid">
                      <div className="info-item">
                        <span className="label">District:</span>
                        <span className="value">{result.district_info.name || 'N/A'}</span>
                      </div>
                      <div className="info-item">
                        <span className="label">Terrain:</span>
                        <span className="value">{result.district_info.terrain_type || 'N/A'}</span>
                      </div>
                      <div className="info-item">
                        <span className="label">Elevation:</span>
                        <span className="value">{result.district_info.elevation || 'N/A'} m</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                {result.recommendation && (
                  <div className="recommendation-card">
                    <h4>💡 Recommendation & Actions</h4>
                    {typeof result.recommendation === 'object' ? (
                      <>
                        {result.recommendation.summary_en && (
                          <p><strong>Summary:</strong> {result.recommendation.summary_en}</p>
                        )}
                        {result.recommendation.immediate_actions && (
                          <p><strong>Immediate Actions:</strong> {result.recommendation.immediate_actions}</p>
                        )}
                        {result.recommendation.agency_notifications && (
                          <p><strong>Agency Notifications:</strong> {result.recommendation.agency_notifications}</p>
                        )}
                        {result.recommendation.preparation_timeline && (
                          <p><strong>Preparation Timeline:</strong> {result.recommendation.preparation_timeline}</p>
                        )}
                        {result.recommendation.evacuation_priority && (
                          <p><strong>Evacuation Priority:</strong> {result.recommendation.evacuation_priority}</p>
                        )}
                      </>
                    ) : (
                      <p>{result.recommendation}</p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📊</div>
                <h3>No Prediction Yet</h3>
                <p>Fill in the form and click "Predict Flood Risk" to see results</p>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>FloodSense AI • Advanced Flood Early Warning System</p>
      </footer>
    </div>
  )
}

export default App