<template>
  <div class="market-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>📊 Real-Time Market Data</h2>
      <div class="connection-status">
        <span :class="['status-dot', { connected: isConnected }]"></span>
        <span class="status-text">{{ isConnected ? 'Live' : 'Disconnected' }}</span>
        <span v-if="lastUpdate" class="last-update">
          {{ formatTime(lastUpdate) }}
        </span>
      </div>
    </div>

    <!-- Alerts Banner -->
    <div v-if="alerts.length" class="alerts-banner">
      <div v-for="(alert, i) in alerts" :key="i" class="alert-item">
        ⚡ <strong>{{ alert.topic }}</strong>: {{ alert.message }}
        <span class="alert-agent">— {{ alert.agent_name }}</span>
      </div>
    </div>

    <!-- Price Grid -->
    <div class="price-grid">
      <div
        v-for="(data, symbol) in prices"
        :key="symbol"
        class="price-card"
        :class="{ positive: data.change > 0, negative: data.change < 0 }"
      >
        <div class="symbol">{{ symbol }}</div>
        <div class="price">{{ formatPrice(data.price) }}</div>
        <div class="change" v-if="data.change != null">
          {{ data.change >= 0 ? '▲' : '▼' }}
          {{ formatChange(data.change) }}
        </div>
        <div class="category-badge">{{ data.category || '—' }}</div>
      </div>
    </div>

    <!-- Sentiment Velocity -->
    <div v-if="velocity.length" class="velocity-section">
      <h3>🔄 Sentiment Velocity (dS/dt)</h3>
      <table class="velocity-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Topic</th>
            <th>Velocity</th>
            <th>Direction</th>
            <th>Rounds</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(v, i) in velocity"
            :key="i"
            :class="{ 'high-velocity': Math.abs(v.velocity) > 0.3 }"
          >
            <td>{{ v.agent_name }}</td>
            <td>{{ v.topic }}</td>
            <td class="velocity-value" :class="{ positive: v.velocity > 0, negative: v.velocity < 0 }">
              {{ v.velocity > 0 ? '+' : '' }}{{ v.velocity.toFixed(3) }}
            </td>
            <td>
              <span v-if="v.velocity > 0.1" class="direction bullish">🟢 Bullish</span>
              <span v-else-if="v.velocity < -0.1" class="direction bearish">🔴 Bearish</span>
              <span v-else class="direction neutral">⚪ Stable</span>
            </td>
            <td>{{ v.data_points || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Fallback Polling (si WebSocket non disponible) -->
    <div v-if="!isConnected && hasFallbackData" class="fallback-notice">
      ℹ️ Using HTTP polling (WebSocket unavailable)
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useMarketWebSocket } from '../composables/useMarketWebSocket'
import { getMarketSnapshot, getSentimentVelocity } from '../api/market'

const {
  prices,
  velocity,
  alerts,
  isConnected,
  lastUpdate,
  formatPrice,
  formatChange,
} = useMarketWebSocket()

const hasFallbackData = ref(false)
let pollTimer = null

// Formatteur de temps
function formatTime(date) {
  if (!date) return ''
  return date.toLocaleTimeString('en-US', { hour12: false })
}

// Fallback: HTTP polling si WebSocket échoue
async function pollData() {
  if (isConnected.value) return // WebSocket actif → pas besoin

  try {
    const [marketRes, velocityRes] = await Promise.all([
      getMarketSnapshot(),
      getSentimentVelocity(),
    ])

    if (marketRes.data?.prices) {
      prices.value = marketRes.data.prices
      hasFallbackData.value = true
    }
    if (velocityRes.data?.signals) {
      velocity.value = velocityRes.data.signals
    }
    if (velocityRes.data?.alerts) {
      alerts.value = velocityRes.data.alerts
    }
    lastUpdate.value = new Date()
  } catch (e) {
    console.warn('[MarketDashboard] Poll failed:', e.message)
  }
}

onMounted(() => {
  // Démarrer le polling comme fallback (s'arrête si WS se connecte)
  pollTimer = setInterval(pollData, 10000) // Toutes les 10s
  pollData() // Premier appel immédiat
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.market-dashboard {
  padding: 1rem;
  font-family: 'Inter', -apple-system, sans-serif;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #888;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.status-dot.connected {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

/* Alerts */
.alerts-banner {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border: 1px solid #f59e0b;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.alert-item {
  font-size: 0.9rem;
  color: #92400e;
}

.alert-agent {
  opacity: 0.7;
  font-style: italic;
}

/* Price Grid */
.price-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.price-card {
  background: #1e1e2e;
  border-radius: 10px;
  padding: 1rem;
  border: 1px solid #333;
  transition: transform 0.15s, border-color 0.2s;
}

.price-card:hover {
  transform: translateY(-2px);
  border-color: #555;
}

.price-card.positive {
  border-left: 3px solid #22c55e;
}

.price-card.negative {
  border-left: 3px solid #ef4444;
}

.price-card .symbol {
  font-weight: 700;
  font-size: 0.85rem;
  color: #ccc;
  text-transform: uppercase;
}

.price-card .price {
  font-size: 1.25rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0.25rem 0;
}

.price-card .change {
  font-size: 0.8rem;
  font-weight: 500;
}

.price-card.positive .change { color: #22c55e; }
.price-card.negative .change { color: #ef4444; }

.category-badge {
  font-size: 0.7rem;
  color: #666;
  margin-top: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Velocity Table */
.velocity-section {
  margin-top: 1.5rem;
}

.velocity-section h3 {
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

.velocity-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.velocity-table th {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 2px solid #333;
  color: #999;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.velocity-table td {
  padding: 0.5rem;
  border-bottom: 1px solid #2a2a3a;
}

.velocity-table tr.high-velocity {
  background: rgba(245, 158, 11, 0.08);
}

.velocity-value.positive { color: #22c55e; font-weight: 600; }
.velocity-value.negative { color: #ef4444; font-weight: 600; }

.direction {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.direction.bullish { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.direction.bearish { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.direction.neutral { background: rgba(156, 163, 175, 0.1); color: #9ca3af; }

/* Fallback Notice */
.fallback-notice {
  text-align: center;
  color: #666;
  font-size: 0.85rem;
  padding: 0.5rem;
  margin-top: 1rem;
}
</style>
