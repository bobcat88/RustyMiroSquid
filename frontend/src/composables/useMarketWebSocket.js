import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Composable pour la connexion WebSocket aux données de marché en temps réel.
 * 
 * Usage:
 *   const { prices, isConnected, error, connect, disconnect } = useMarketWebSocket()
 * 
 * @param {Object} options
 * @param {string} options.url - WebSocket URL (default: ws://localhost:5001/ws/market)
 * @param {number} options.reconnectDelay - Délai de reconnexion en ms (default: 3000)
 * @param {number} options.maxRetries - Nombre max de tentatives (default: 5)
 */
export function useMarketWebSocket(options = {}) {
  const {
    url = `ws://${window.location.hostname}:5001/ws/market`,
    reconnectDelay = 3000,
    maxRetries = 5,
  } = options

  const prices = ref({})
  const velocity = ref([])
  const alerts = ref([])
  const isConnected = ref(false)
  const error = ref(null)
  const lastUpdate = ref(null)

  let ws = null
  let retryCount = 0
  let reconnectTimer = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    try {
      ws = new WebSocket(url)

      ws.onopen = () => {
        isConnected.value = true
        error.value = null
        retryCount = 0
        console.log('[MarketWS] Connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastUpdate.value = new Date()

          if (data.type === 'price_update') {
            // Mise à jour incrémentale des prix
            prices.value = { ...prices.value, ...data.prices }
          } else if (data.type === 'velocity_update') {
            velocity.value = data.signals || []
            alerts.value = data.alerts || []
          } else if (data.type === 'snapshot') {
            // Snapshot complet (envoyé à la connexion)
            prices.value = data.prices || {}
            velocity.value = data.velocity || []
            alerts.value = data.alerts || []
          }
        } catch (e) {
          console.warn('[MarketWS] Parse error:', e)
        }
      }

      ws.onerror = (e) => {
        error.value = 'WebSocket error'
        console.error('[MarketWS] Error:', e)
      }

      ws.onclose = (event) => {
        isConnected.value = false
        console.log(`[MarketWS] Closed (code: ${event.code})`)

        // Reconnexion automatique
        if (retryCount < maxRetries && !event.wasClean) {
          retryCount++
          const delay = reconnectDelay * Math.min(retryCount, 3)
          console.log(`[MarketWS] Reconnecting in ${delay}ms (attempt ${retryCount}/${maxRetries})`)
          reconnectTimer = setTimeout(connect, delay)
        }
      }
    } catch (e) {
      error.value = e.message
      console.error('[MarketWS] Connection failed:', e)
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    retryCount = maxRetries // Empêcher la reconnexion
    if (ws) {
      ws.close(1000, 'Client disconnect')
      ws = null
    }
    isConnected.value = false
  }

  // Formatteur pour l'affichage des prix
  function formatPrice(price, currency = 'USD') {
    if (price == null) return '—'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: price < 1 ? 6 : 2,
    }).format(price)
  }

  // Formatteur pour les variations en pourcentage
  function formatChange(change) {
    if (change == null) return '—'
    const sign = change >= 0 ? '+' : ''
    return `${sign}${(change * 100).toFixed(2)}%`
  }

  onMounted(() => connect())
  onUnmounted(() => disconnect())

  return {
    prices,
    velocity,
    alerts,
    isConnected,
    error,
    lastUpdate,
    connect,
    disconnect,
    formatPrice,
    formatChange,
  }
}
