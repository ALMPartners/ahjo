# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Frozen-executable entry point for the Ahjo upgrade worker.

This thin wrapper exists so cx_Freeze can build a standalone
``ahjo-upgrade-worker.exe`` for the MSI installer. The frozen executable
is invoked as a subprocess by :class:`ahjo.operations.general.upgrade.AhjoUpgrade`
when Ahjo itself is running from a frozen build (where ``sys.executable``
is an Ahjo .exe, not a Python interpreter, and therefore ``python -m`` is
not available).

It is not intended for direct end-user invocation.
"""

from ahjo.operations.general.upgrade_worker import main


if __name__ == "__main__":
    main()
