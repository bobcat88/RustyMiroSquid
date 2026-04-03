"""
Migration script: json stdlib → orjson (Rust-native)

Ce script migre automatiquement tous les fichiers Python dans backend/app/
et backend/scripts/ de `import json` vers `import orjson`.

Patterns de migration:
- import json                          → import orjson
- orjson.loads(x)                        → ororjson.loads(x)
- ororjson.dumps(x).decode()    → ororjson.dumps(x).decode()
- orjson.dumps(x, ..., indent=2)         → ororjson.dumps(x, option=orjson.OPT_INDENT_2).decode()
- orjson.loads(f.read())                         → ororjson.loads(f.read())
- json.dump(x, f, ...)                 → f.write(ororjson.dumps(x, option=orjson.OPT_INDENT_2).decode())

IMPORTANT:
- Ne migre PAS les fichiers dans backend/wonderwall/ (CAMEL-AI interne)
- Ne migre PAS flask.jsonify (c'est du Flask interne)
- Garde `import json` si orjson.JSONDecodeError est utilisé (rare)
"""

import re
from pathlib import Path

# Dossiers à migrer
DIRS_TO_MIGRATE = [
    Path("app"),
    Path("scripts"),
]

# Dossiers à NE PAS toucher
DIRS_TO_SKIP = [
    "wonderwall",
    "__pycache__",
    ".venv",
]

def should_skip(path: Path) -> bool:
    """Ne pas migrer les fichiers dans wonderwall ou __pycache__."""
    parts = path.parts
    return any(skip in parts for skip in DIRS_TO_SKIP)


def migrate_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Migre un fichier Python de json vers orjson.
    
    Returns:
        (was_modified, list_of_changes)
    """
    content = filepath.read_text(encoding="utf-8")
    original = content
    changes = []
    
    # Vérifier que le fichier utilise json
    if "import json" not in content:
        return False, []
    
    # Ne pas migrer si orjson.JSONDecodeError est utilisé seul
    uses_json_decode_error = "orjson.JSONDecodeError" in content or "JSONDecodeError" in content
    
    # 1. Remplacer l'import
    if "import json\n" in content:
        content = content.replace("import json\n", "import orjson\n", 1)
        changes.append("import json → import orjson")
    
    # Gérer les imports locaux (dans des fonctions)
    # Pattern: "        import json" (indented)
    content = re.sub(r'^(\s+)import json$', r'\1import orjson', content, flags=re.MULTILINE)
    
    # 2. json.loads → orjson.loads (drop-in)
    content = content.replace("orjson.loads(", "ororjson.loads(")
    if "ororjson.loads(" in content and "orjson.loads(" in original:
        changes.append("json.loads → orjson.loads")
    
    # 3. json.dumps avec indent → orjson.dumps avec OPT_INDENT_2
    # Pattern: ororjson.dumps(xxx, option=orjson.OPT_INDENT_2).decode()
    content = re.sub(
        r'json\.dumps\(([^)]+?),\s*ensure_ascii\s*=\s*False\s*,\s*indent\s*=\s*(\d+)\)',
        r'ororjson.dumps(\1, option=orjson.OPT_INDENT_2).decode()',
        content
    )
    # Pattern: ororjson.dumps(xxx, option=orjson.OPT_INDENT_2).decode()
    content = re.sub(
        r'json\.dumps\(([^)]+?),\s*indent\s*=\s*(\d+)\s*,\s*ensure_ascii\s*=\s*False\)',
        r'ororjson.dumps(\1, option=orjson.OPT_INDENT_2).decode()',
        content
    )
    # Pattern: orjson.dumps(xxx, indent=indent) — variable indent
    content = re.sub(
        r'json\.dumps\(([^)]+?),\s*ensure_ascii\s*=\s*False\s*,\s*indent\s*=\s*indent\)',
        r'ororjson.dumps(\1, option=orjson.OPT_INDENT_2).decode()',
        content
    )
    
    # 4. json.dumps sans indent → ororjson.dumps().decode()
    # Pattern: ororjson.dumps(xxx).decode()
    content = re.sub(
        r'json\.dumps\(([^)]+?),\s*ensure_ascii\s*=\s*False\)',
        r'ororjson.dumps(\1).decode()',
        content
    )
    # Pattern: orjson.dumps(xxx) simple
    content = content.replace("orjson.dumps(", "ororjson.dumps(")
    # Ajouter .decode() là où manquant
    # On le fait manuellement plus tard si nécessaire
    
    if "ororjson.dumps(" in content and "orjson.dumps(" in original:
        changes.append("json.dumps → ororjson.dumps().decode()")
    
    # 5. orjson.loads(f.read()) → ororjson.loads(f.read())
    content = re.sub(
        r'json\.load\((\w+)\)',
        r'ororjson.loads(\1.read())',
        content
    )
    if "ororjson.loads(" in content and "json.load(" in original:
        changes.append("orjson.loads(f.read()) → ororjson.loads(f.read())")
    
    # 6. json.dump(data, f, ...) → f.write(ororjson.dumps(data, ...).decode())
    # Pattern: f.write(orjson.dumps(xxx, option=orjson.OPT_INDENT_2).decode())
    content = re.sub(
        r'json\.dump\(([^,]+),\s*(\w+)\s*,\s*ensure_ascii\s*=\s*False\s*,\s*indent\s*=\s*\d+\)',
        r'\2.write(ororjson.dumps(\1, option=orjson.OPT_INDENT_2).decode())',
        content
    )
    # Pattern: f.write(orjson.dumps(xxx, option=orjson.OPT_INDENT_2).decode())
    content = re.sub(
        r'json\.dump\(([^,]+),\s*(\w+)\s*,\s*indent\s*=\s*\d+\s*,\s*ensure_ascii\s*=\s*False\)',
        r'\2.write(ororjson.dumps(\1, option=orjson.OPT_INDENT_2).decode())',
        content
    )
    # Pattern: f.write(orjson.dumps(xxx).decode()) simple
    content = re.sub(
        r'json\.dump\(([^,]+),\s*(\w+)\)',
        r'\2.write(ororjson.dumps(\1).decode())',
        content
    )
    if "f.write(orjson" in content or ".write(orjson" in content:
        if "f.write(orjson.dumps(" in original:
            changes.append("json.dump(data).decode()) → f.write(ororjson.dumps(data).decode())")
    
    # 7. Replacer orjson.JSONDecodeError par ororjson.JSONDecodeError (n'existe pas)
    # orjson lève une ororjson.JSONDecodeError, donc on peut garder le pattern
    # mais on doit vérifier que ça marche
    if uses_json_decode_error:
        content = content.replace("orjson.JSONDecodeError", "ororjson.JSONDecodeError")
        changes.append("orjson.JSONDecodeError → ororjson.JSONDecodeError")
    
    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return True, changes
    
    return False, []


def main():
    """Exécute la migration sur tous les fichiers."""
    root = Path(__file__).parent.parent  # backend/scripts/ → backend/
    total_modified = 0
    total_skipped = 0
    
    for dir_path in DIRS_TO_MIGRATE:
        full_dir = root / dir_path
        if not full_dir.exists():
            print(f"SKIP (not found): {dir_path}")
            continue
        
        for py_file in sorted(full_dir.rglob("*.py")):
            if should_skip(py_file):
                continue
            
            modified, changes = migrate_file(py_file)
            rel_path = py_file.relative_to(root)
            
            if modified:
                total_modified += 1
                print(f"✅ {rel_path}")
                for change in changes:
                    print(f"   └─ {change}")
            elif "import json" in py_file.read_text(encoding="utf-8"):
                total_skipped += 1
                print(f"⏭️  {rel_path} (no json usage found)")
    
    print(f"\n{'='*50}")
    print(f"Migration terminée: {total_modified} fichiers modifiés, {total_skipped} skippés")


if __name__ == "__main__":
    main()
