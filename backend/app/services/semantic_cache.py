"""
Semantic Cache — Cache Redis de raisonnements LLM par similarité sémantique.

Cache les réponses LLM avec un TTL configurable. Utilise un hash rapide
du prompt comme clé primaire, avec support optionnel de la similarité
cosinus pour le cache sémantique avancé.

Usage:
    cache = SemanticCache()

    # Vérifier le cache avant d'appeler le LLM
    cached = await cache.get(prompt)
    if cached:
        return cached

    # Stocker la réponse après appel LLM
    response = await llm.chat(prompt)
    await cache.put(prompt, response)

    # Invalidation par pattern
    await cache.invalidate_pattern("simulation:*")
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Optional

import orjson

logger = logging.getLogger(__name__)


class SemanticCache:
    """Cache Redis pour les raisonnements LLM.

    Stratégie de cache:
    - Hash SHA-256 du prompt normalisé comme clé primaire (lookup exact, O(1))
    - TTL configurable par entrée (default: 1h)
    - Namespace par type de requête (simulation, analysis, compaction)
    - Métriques hit/miss intégrées

    Args:
        redis_url: URL de connexion Redis (redis://host:port/db).
        default_ttl: TTL par défaut en secondes (3600 = 1h).
        namespace: Préfixe des clés Redis pour isolation.
        max_prompt_length: Longueur max du prompt à hasher (troncature).
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        namespace: str = "squid:llm_cache",
        max_prompt_length: int = 8000,
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.namespace = namespace
        self.max_prompt_length = max_prompt_length

        self._redis = None
        self._initialized = False

        # Métriques en mémoire
        self._hits = 0
        self._misses = 0
        self._puts = 0
        self._errors = 0

    async def _lazy_init(self):
        """Initialisation paresseuse — connexion Redis au premier appel."""
        if self._initialized:
            return

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=False,  # On utilise orjson (bytes)
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test de connexion
            await self._redis.ping()
            self._initialized = True
            logger.info(f"SemanticCache connecté à {self.redis_url}")
        except ImportError:
            logger.warning(
                "redis[async] non installé. Cache désactivé. "
                "Installer avec: uv add redis"
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Erreur connexion Redis: {e}")
            self._initialized = True

    def _make_key(self, prompt: str, context: str = "") -> str:
        """Générer une clé de cache à partir du prompt.

        Normalise le prompt (strip, lowercase) puis hash SHA-256.
        Le contexte optionnel permet de différencier les mêmes prompts
        dans des situations différentes.

        Args:
            prompt: Le prompt LLM à hasher.
            context: Contexte additionnel (ex: "simulation_round_5").

        Returns:
            Clé Redis complète (namespace:hash).
        """
        # Normalisation
        normalized = prompt.strip().lower()
        if len(normalized) > self.max_prompt_length:
            normalized = normalized[:self.max_prompt_length]

        # Hash avec contexte
        to_hash = f"{context}:{normalized}" if context else normalized
        digest = hashlib.sha256(to_hash.encode("utf-8")).hexdigest()[:16]

        return f"{self.namespace}:{digest}"

    async def get(
        self,
        prompt: str,
        context: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Récupérer une réponse cachée.

        Args:
            prompt: Le prompt LLM.
            context: Contexte additionnel pour la clé.

        Returns:
            Dict avec la réponse cachée, ou None si miss.
        """
        await self._lazy_init()

        if self._redis is None:
            self._misses += 1
            return None

        key = self._make_key(prompt, context)

        try:
            data = await self._redis.get(key)
            if data is None:
                self._misses += 1
                return None

            entry = orjson.loads(data)
            self._hits += 1

            logger.debug(
                f"Cache HIT: {key} "
                f"(âge: {time.time() - entry.get('timestamp', 0):.0f}s)"
            )

            return {
                "response": entry["response"],
                "cached": True,
                "cache_age": time.time() - entry.get("timestamp", 0),
                "model": entry.get("model", "unknown"),
            }

        except Exception as e:
            self._errors += 1
            logger.warning(f"Erreur lecture cache: {e}")
            return None

    async def put(
        self,
        prompt: str,
        response: str,
        context: str = "",
        ttl: Optional[int] = None,
        model: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Stocker une réponse dans le cache.

        Args:
            prompt: Le prompt LLM (utilisé pour la clé).
            response: La réponse LLM à cacher.
            context: Contexte additionnel pour la clé.
            ttl: TTL en secondes. None = default_ttl.
            model: Nom du modèle LLM utilisé.
            metadata: Métadonnées additionnelles (tokens, latence, etc.).

        Returns:
            True si succès, False sinon.
        """
        await self._lazy_init()

        if self._redis is None:
            return False

        key = self._make_key(prompt, context)
        effective_ttl = ttl if ttl is not None else self.default_ttl

        entry = {
            "response": response,
            "timestamp": time.time(),
            "model": model,
            "prompt_length": len(prompt),
        }
        if metadata:
            entry["metadata"] = metadata

        try:
            data = orjson.dumps(entry)
            await self._redis.setex(key, effective_ttl, data)
            self._puts += 1

            logger.debug(
                f"Cache PUT: {key} (TTL: {effective_ttl}s, "
                f"taille: {len(data)} bytes)"
            )
            return True

        except Exception as e:
            self._errors += 1
            logger.warning(f"Erreur écriture cache: {e}")
            return False

    async def invalidate(self, prompt: str, context: str = "") -> bool:
        """Invalider une entrée spécifique du cache.

        Args:
            prompt: Le prompt dont la réponse doit être invalidée.
            context: Contexte additionnel.

        Returns:
            True si l'entrée existait et a été supprimée.
        """
        await self._lazy_init()

        if self._redis is None:
            return False

        key = self._make_key(prompt, context)

        try:
            deleted = await self._redis.delete(key)
            if deleted:
                logger.info(f"Cache INVALIDATE: {key}")
            return deleted > 0
        except Exception as e:
            self._errors += 1
            logger.warning(f"Erreur invalidation cache: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalider toutes les entrées correspondant à un pattern.

        Args:
            pattern: Pattern Redis (ex: "squid:llm_cache:*").

        Returns:
            Nombre d'entrées supprimées.
        """
        await self._lazy_init()

        if self._redis is None:
            return 0

        full_pattern = f"{self.namespace}:{pattern}"

        try:
            keys = []
            async for key in self._redis.scan_iter(match=full_pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(
                    f"Cache INVALIDATE_PATTERN: {full_pattern} "
                    f"({deleted} entrées supprimées)"
                )
                return deleted
            return 0

        except Exception as e:
            self._errors += 1
            logger.warning(f"Erreur invalidation pattern: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Métriques de performance du cache.

        Returns:
            Dict avec hits, misses, ratio, puts, errors.
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 1),
            "puts": self._puts,
            "errors": self._errors,
            "total_requests": total,
            "connected": self._redis is not None,
            "namespace": self.namespace,
            "default_ttl": self.default_ttl,
        }

    async def close(self):
        """Fermer la connexion Redis proprement."""
        if self._redis:
            await self._redis.close()
            logger.info("SemanticCache: connexion Redis fermée")
