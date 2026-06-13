# brief.py
# Legacy compatibility wrapper redirecting to modular pipeline in main.py
import asyncio
import sys
from logger import log
from main import run_pipeline

if __name__ == "__main__":
    log.info("Executing modular pipeline via brief.py compatibility wrapper...")
    try:
        asyncio.run(run_pipeline())
    except Exception as e:
        log.error(f"Error executing pipeline: {e}")
        sys.exit(1)
