# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Operations common to all database backends.
"""

from ahjo.operations.general.alembic import (
    downgrade_db_to_alembic_base,
    print_alembic_version,
    upgrade_db_to_latest_alembic_version
    )

from ahjo.operations.general.bulk_insert import (
    bulk_insert_into_database
    )

from ahjo.operations.general.git_version import (
    print_git_version,
    update_git_version
    )

from ahjo.operations.general.initialization import (
    create_local_config_base,
    create_new_project,
    populate_project
    )
