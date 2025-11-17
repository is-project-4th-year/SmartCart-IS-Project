#!/usr/bin/env python
import os
import sys

db_path = '/Users/cyrilmugada/Documents/market/smartcart/instance/smartcart_dev.db'

if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print("✓ Database deleted successfully")
    except Exception as e:
        print(f"✗ Error deleting database: {e}")
        sys.exit(1)
else:
    print("✓ Database not found (clean state)")

sys.exit(0)