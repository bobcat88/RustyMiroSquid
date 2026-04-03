"""
Prompt Compressor — Middleware de compression de prompt pour réduire le coût en tokens.

Utilise LLMLingua pour compresser les contextes volumineux (> seuil configurable)
avant envoi au LLM, avec protection des données financières critiques.

Usage:
    compressor = PromptCompressor()

    # Compresser un prompt long avant envoi au LLM
    compressed = compressor.compress(long_context, target_ratio=0.5)

    # Compresser uniquement si > seuil
    result = compressor.compress_if_needed(prompt, threshold_tokens=2000)
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Patterns de données financières à préserver (jamais compressés)
_FINANCIAL_PATTERNS = [
    r"\$[\d,]+\.?\d*",          # Montants en dollars ($1,234.56)
    r"€[\d,]+\.?\d*",          # Montants en euros
    r"\d+\.?\d*\s*%",          # Pourcentages
    r"\d{4}-\d{2}-\d{2}",     # Dates ISO (2026-04-03)
    r"Q[1-4]\s*\d{4}",        # Trimestres (Q1 2026)
    r"FY\d{2,4}",             # Années fiscales (FY2026)
    r"market\s*#\d+",         # IDs de marchés Polymarket
    r"ROI|IRR|NPV|EBITDA|P/E|EPS",  # Métriques financières
]

_FINANCIAL_REGEX = re.compile("|".join(_FINANCIAL_PATTERNS), re.IGNORECASE)


class PromptCompressor:
    """Middleware de compression de prompt intelligent.

    Compresse les contextes volumineux tout en préservant les données
    financières critiques (montants, dates, métriques).

    Args:
        model_name: Modèle LLMLingua à utiliser pour la compression.
        device: Device PyTorch ('cpu', 'cuda', 'mps').
        default_ratio: Ratio de compression par défaut (0.5 = 50% de réduction).
        threshold_tokens: Seuil en tokens au-dessus duquel la compression s'active.
    """

    def __init__(
        self,
        model_name: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        device: str = "cpu",
        default_ratio: float = 0.5,
        threshold_tokens: int = 2000,
    ):
        self.model_name = model_name
        self.device = device
        self.default_ratio = default_ratio
        self.threshold_tokens = threshold_tokens
        self._compressor = None
        self._initialized = False

    def _lazy_init(self):
        """Initialisation paresseuse — charge LLMLingua au premier appel."""
        if self._initialized:
            return

        try:
            from llmlingua import PromptCompressor as LLMLinguaCompressor

            self._compressor = LLMLinguaCompressor(
                model_name=self.model_name,
                device_map=self.device,
                use_llmlingua2=True,
            )
            self._initialized = True
            logger.info(
                f"PromptCompressor initialisé avec {self.model_name} "
                f"sur {self.device}"
            )
        except ImportError:
            logger.warning(
                "LLMLingua non installé. Compression désactivée. "
                "Installer avec: uv add llmlingua"
            )
            self._initialized = True  # Évite de retenter
        except Exception as e:
            logger.error(f"Erreur initialisation LLMLingua: {e}")
            self._initialized = True

    def _estimate_tokens(self, text: str) -> int:
        """Estimation rapide du nombre de tokens (1 token ≈ 4 chars en anglais)."""
        return len(text) // 4

    def _extract_protected_segments(self, text: str) -> List[Dict[str, Any]]:
        """Extraire les segments financiers à protéger de la compression.

        Returns:
            Liste de dicts {start, end, text} pour chaque segment protégé.
        """
        segments = []
        for match in _FINANCIAL_REGEX.finditer(text):
            segments.append({
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
            })
        return segments

    def compress(
        self,
        text: str,
        target_ratio: Optional[float] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Compresser un texte avec LLMLingua.

        Args:
            text: Texte à compresser.
            target_ratio: Ratio de compression (0.3 = garder 30%). None = default.
            force: Forcer la compression même sous le seuil.

        Returns:
            Dict avec:
                - compressed_text: Texte compressé
                - original_tokens: Estimation tokens originaux
                - compressed_tokens: Estimation tokens compressés
                - ratio: Ratio de compression réel
                - savings_pct: Pourcentage d'économie
                - was_compressed: Si la compression a eu lieu
                - protected_count: Nombre de segments financiers préservés
        """
        self._lazy_init()

        original_tokens = self._estimate_tokens(text)
        ratio = target_ratio or self.default_ratio

        # Pas de compression si sous le seuil (sauf force)
        if not force and original_tokens <= self.threshold_tokens:
            return {
                "compressed_text": text,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "ratio": 1.0,
                "savings_pct": 0.0,
                "was_compressed": False,
                "protected_count": 0,
            }

        # Pas de compresseur disponible — retourner le texte tel quel
        if self._compressor is None:
            logger.debug("Compression ignorée (LLMLingua non disponible)")
            return {
                "compressed_text": text,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "ratio": 1.0,
                "savings_pct": 0.0,
                "was_compressed": False,
                "protected_count": 0,
            }

        # Identifier les segments financiers à protéger
        protected = self._extract_protected_segments(text)

        start_time = time.perf_counter()

        try:
            result = self._compressor.compress_prompt(
                text,
                rate=ratio,
                force_tokens=[seg["text"] for seg in protected],
            )

            compressed_text = result.get("compressed_prompt", text)
            compressed_tokens = self._estimate_tokens(compressed_text)
            elapsed = time.perf_counter() - start_time

            actual_ratio = compressed_tokens / max(original_tokens, 1)
            savings = (1 - actual_ratio) * 100

            logger.info(
                f"Compression: {original_tokens} → {compressed_tokens} tokens "
                f"({savings:.1f}% économie) en {elapsed:.2f}s, "
                f"{len(protected)} segments financiers préservés"
            )

            return {
                "compressed_text": compressed_text,
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "ratio": actual_ratio,
                "savings_pct": savings,
                "was_compressed": True,
                "protected_count": len(protected),
            }

        except Exception as e:
            logger.error(f"Erreur compression: {e}")
            return {
                "compressed_text": text,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "ratio": 1.0,
                "savings_pct": 0.0,
                "was_compressed": False,
                "protected_count": 0,
            }

    def compress_if_needed(
        self,
        text: str,
        threshold_tokens: Optional[int] = None,
    ) -> str:
        """Compresser uniquement si le texte dépasse le seuil.

        Raccourci pratique qui retourne directement le texte compressé.

        Args:
            text: Texte à potentiellement compresser.
            threshold_tokens: Seuil personnalisé. None = self.threshold_tokens.

        Returns:
            Texte compressé ou original.
        """
        threshold = threshold_tokens or self.threshold_tokens
        if self._estimate_tokens(text) <= threshold:
            return text

        result = self.compress(text, force=True)
        return result["compressed_text"]

    def get_stats(self) -> Dict[str, Any]:
        """Retourner l'état du compresseur."""
        return {
            "initialized": self._initialized,
            "model": self.model_name,
            "device": self.device,
            "available": self._compressor is not None,
            "default_ratio": self.default_ratio,
            "threshold_tokens": self.threshold_tokens,
        }
