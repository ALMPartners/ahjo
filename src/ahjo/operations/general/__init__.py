# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Operations common to all database backends.
"""

from ahjo.operations.general.alembic import (
    downgrade_db_to_alembic_base,
    print_alembic_version,
    upgrade_db_to_latest_alembic_version,
    alembic_command
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

from ahjo.operations.general.sqlfiles import (
    deploy_sqlfiles,
    drop_sqlfile_objects,
    deploy_sql_from_file,
    create_dependency_graph
)

from ahjo.operations.general.upgrade import (
    AhjoUpgrade
)

from ahjo.operations.general.db_info import (
    print_db_collation
)

from ahjo.operations.general.scan import (
    AhjoScan
)

from ahjo.operations.general.db_tester import (
    DatabaseTester
)

from ahjo.operations.general.visualization import (
    plot_dependency_graph
)