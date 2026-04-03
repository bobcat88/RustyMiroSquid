"""
MiroShark Backend entry point
"""

import os
import sys

# Fix Windows console encoding issues: set UTF-8 encoding before all imports
if sys.platform == 'win32':
    # Set environment variable to ensure Python uses UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Reconfigure standard output streams to UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import Config
import uvicorn


def main():
    """Main function"""
    # Validate configuration
    errors = Config.validate()
    if errors:
        print("Configuration errors:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease check the configuration in your .env file")
        sys.exit(1)
    
    # Get runtime configuration
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5001))
    
    # Check if hardware setup is needed (check if torch is installed)
    try:
        import torch
        logger_info = "Hardware-accelerated environment detected."
    except ImportError:
        print("\n[NOTE] ML dependencies (Torch, sentence-transformers, etc.) not found.")
        print("Run 'uv run python scripts/setup_hardware.py' to optimize for your GPU/CPU.")
    
    # Start server with uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=Config.DEBUG)


if __name__ == '__main__':
    main()

