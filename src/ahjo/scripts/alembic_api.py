# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import sys
from alembic.config import main

try:
    from ahjo.version import version as AHJO_VERSION
except ImportError:
    AHJO_VERSION = "?.?.?"

# Indicator for a frozen executable (e.g. running from an msi installation)
CX_FROZEN_TAG = " (frozen)" if getattr(sys, "frozen", False) else ""

info_msg = f"    Alembic API for Ahjo v{AHJO_VERSION}{CX_FROZEN_TAG}"
line = "-" * len(info_msg)
print(line)
print(info_msg)
print(line)

if __name__ == "__main__":
    main()
