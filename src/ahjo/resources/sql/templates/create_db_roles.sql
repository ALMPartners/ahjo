/*
    THIS IS AHJO SQL SCRIPT TEMPLATE (MSSQL)
    ================================
    USE THIS TEMPLATE AS AN EXAMPLE
    WHEN CREATING YOUR OWN SCRIPTS.
*/
/*

-- Create database role with hardcoded values
IF DATABASE_PRINCIPAL_ID('AHJO_ROLE') IS NULL
    BEGIN
        CREATE ROLE AHJO_ROLE  
    END

-- Create database role with scripting variables
IF DATABASE_PRINCIPAL_ID('$(example_role_name)') IS NULL
    BEGIN
        CREATE ROLE $(example_role_name)
    END

GO

*/