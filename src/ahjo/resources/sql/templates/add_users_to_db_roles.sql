/*
    THIS IS AHJO SQL SCRIPT TEMPLATE (MSSQL)
    ================================
    USE THIS TEMPLATE AS AN EXAMPLE
    WHEN CREATING YOUR OWN SCRIPTS.
*/
/*

-- Add user to role with hardcoded values
ALTER ROLE [AHJO_ROLE]
    ADD MEMBER [AHJO_USER]

-- Add user to role with scripting variables
ALTER ROLE [$(example_role_name]
    ADD MEMBER [$(example_user_name)]

GO

*/