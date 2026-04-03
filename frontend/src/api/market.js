import service from './index'

/**
 * Récupérer les données de marché en temps réel (snapshot)
 * @returns {Promise<{prices: Object, watchlist: Object, last_update: string}>}
 */
export const getMarketSnapshot = () => {
  return service.get('/api/market/snapshot')
}

/**
 * Récupérer les signaux de vélocité de sentiment
 * @param {number} topN - Nombre de signaux à retourner
 * @returns {Promise<{signals: Array, alerts: Array}>}
 */
export const getSentimentVelocity = (topN = 10) => {
  return service.get('/api/market/velocity', { params: { top_n: topN } })
}

/**
 * Récupérer la watchlist configurée
 * @returns {Promise<{watchlist: Object}>}
 */
export const getWatchlist = () => {
  return service.get('/api/market/watchlist')
}

/**
 * Ajouter un ticker à la watchlist
 * @param {Object} data - { symbol: string, category: string }
 */
export const addToWatchlist = (data) => {
  return service.post('/api/market/watchlist/add', data)
}

/**
 * Supprimer un ticker de la watchlist
 * @param {Object} data - { symbol: string }
 */
export const removeFromWatchlist = (data) => {
  return service.post('/api/market/watchlist/remove', data)
}
