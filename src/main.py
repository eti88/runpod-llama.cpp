#!/usr/bin/env python3
"""
Main application entrypoint - placeholder for future integration.
This will run alongside llama-server managed by supervisor.
"""
import time
import sys

def main():
    print("Main application started - placeholder")
    print("llama-server is managed by supervisor and accessible at http://localhost:8000/v1")
    
    # Keep the container running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
