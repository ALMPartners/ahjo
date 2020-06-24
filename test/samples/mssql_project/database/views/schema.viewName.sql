/** 
    THIS IS AHJO SQL SCRIPT TEMPLATE 
    ================================
    USE THIS TEMPLATE AS AN EXAMPLE
    WHEN CREATING YOUR OWN SCRIPTS.

    NAMING CONVENTION:
    <schema>.<object name>.sql
*/

-- First, drop view

/**
IF OBJECT_ID('schema.viewName', 'V') IS NOT NULL
DROP VIEW [schema].[viewName];
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


-- Second, create view

CREATE PROCEDURE [schema].[viewName] 
AS


... view logic here ...


GO
*/