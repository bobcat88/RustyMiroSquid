"""
Text Processing Service
"""

from typing import List
from ..utils.file_parser import FileParser, split_text_into_chunks


class TextProcessor:
    """Text Processor"""

    @staticmethod
    def extract_from_files(file_paths: List[str]) -> str:
        """Extract text from multiple files"""
        return FileParser.extract_from_multiple(file_paths)

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Original text
            chunk_size: Chunk size
            overlap: Overlap size

        Returns:
            List of text chunks
        """
        return split_text_into_chunks(text, chunk_size, overlap)

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess text — strips token-wasting artifacts before LLM ingestion.

        Filters (in order):
        1. Base64 data URIs (embedded images in PDFs/HTML)
        2. <script> and <style> blocks
        3. Navigation boilerplate (cookie banners, copyright, social links)
        4. HTML entities and residual tags
        5. Normalize line breaks
        6. Collapse excessive blank lines
        7. Deduplicate repeated lines (headers/footers in multi-page PDFs)
        8. Strip per-line whitespace

        Args:
            text: Original text

        Returns:
            Processed text
        """
        import re

        # --- Base64 data URIs (PDFs sometimes embed images) ---
        text = re.sub(
            r'data:[a-z]+/[a-z+\-.]+;base64,[A-Za-z0-9+/=]{50,}',
            '[base64-removed]', text, flags=re.IGNORECASE
        )
        text = re.sub(
            r'!\[.*?\]\(data:[^)]+\)',
            '[image-removed]', text, flags=re.IGNORECASE
        )

        # --- Script and style blocks ---
        text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<style[\s\S]*?</style>', '', text, flags=re.IGNORECASE)

        # --- Navigation boilerplate ---
        boilerplate_patterns = [
            r'^\s*(skip\s*to|hyppää|siirry)\s*(content|main|navigation|sisältöön).*',
            r'^\s*(we use cookies|this site uses cookies|cookie policy|accept(ing)? cookies).*',
            r'^\s*(all rights reserved|©\s*\d{4}|copyright\s*\d{4}).*',
            r'^\s*(follow us on|like us on|facebook|twitter/x|instagram|linkedin|youtube|tiktok)\s*$',
            r'^\s*(powered by|made with|built with)\s*.{0,60}$',
            r'^\s*(sitemap|xml sitemap|breadcrumb):?.*',
            r'^\s*(loading|please wait)\s*.{0,20}$',
        ]
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # --- HTML entities and residual tags ---
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        text = re.sub(r'&#\d+;', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]{1,150}>', ' ', text)

        # --- Normalize line breaks ---
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # --- Collapse excessive blank lines ---
        text = re.sub(r'\n{3,}', '\n\n', text)

        # --- Deduplicate repeated lines (e.g. headers/footers in PDFs) ---
        lines = text.split('\n')
        seen_counts: dict[str, int] = {}
        deduped: list[str] = []
        for line in lines:
            key = line.strip().lower()
            if len(key) < 8:
                deduped.append(line)
                continue
            count = seen_counts.get(key, 0)
            if count < 2:
                deduped.append(line)
                seen_counts[key] = count + 1
        text = '\n'.join(deduped)

        # --- Strip per-line whitespace ---
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    @staticmethod
    def get_text_stats(text: str) -> dict:
        """Get text statistics"""
        return {
            "total_chars": len(text),
            "total_lines": text.count('\n') + 1,
            "total_words": len(text.split()),
        }
