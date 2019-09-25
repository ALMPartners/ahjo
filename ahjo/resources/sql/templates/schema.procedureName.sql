/** 
    THIS IS AHJO SQL SCRIPT TEMPLATE 
    ================================
    USE THIS TEMPLATE AS AN EXAMPLE
    WHEN CREATING YOUR OWN SCRIPTS.

    NAMING CONVENTION:
    <schema>.<object name>.sql
*/

-- First, drop procedure

/**
IF OBJECT_ID('schema.procedureName', 'P') IS NOT NULL
    DROP PROCEDURE [schema].[procedureName];
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


-- Second, create procedure

CREATE PROCEDURE [schema].[procedureName] AS
SET NOCOUNT ON;


... procedure logic here ...


SET NOCOUNT OFF;
GO
*/
