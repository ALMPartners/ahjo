/** 
    THIS IS AHJO SQL SCRIPT TEMPLATE 
    ================================
    USE THIS TEMPLATE AS AN EXAMPLE
    WHEN CREATING YOUR OWN SCRIPTS.

    NAMING CONVENTION:
    <schema>.<object name>.sql
*/

-- First, drop function

/**
IF EXISTS (
    SELECT * FROM sysobjects WHERE id = object_id(N'schema.functionName') 
    AND xtype IN (N'FN', N'IF', N'TF')
)
    DROP FUNCTION [schema].[functionName]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


-- Second, create function

CREATE FUNCTION [schema].[functionName] (@param1 INT, @param2 INT)
RETURNS INT
AS
BEGIN
    DECLARE @output INT
    ... function logic here ...

    RETURN @output
END


GO
*/
