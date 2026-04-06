"""
RustyMiroSquid Backend entry point
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

import uvicorn
from app.config import Config

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
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))
    debug = Config.DEBUG
    
    # Start server with Uvicorn
    uvicorn.run(
        "app:create_app",
        host=host, 
        port=port, 
        reload=debug,
        factory=True,
        log_level="debug" if debug else "info"
    )

if __name__ == '__main__':
    main()

