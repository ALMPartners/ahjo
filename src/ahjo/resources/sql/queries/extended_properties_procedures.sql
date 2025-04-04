/**
# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT
    SCHEMA_NAME(s.[schema_id]) AS [schema_name]
    ,s.[name] AS [object_name]
    ,'procedure' AS [object_type]
    ,CONVERT(VARCHAR(8000), e.[name]) AS [property_name]
    ,CONVERT(VARCHAR(8000), e.[value]) AS [property_value]
FROM sys.procedures AS s
    LEFT JOIN sys.extended_properties AS e
        ON e.[major_id] = s.[object_id]
WHERE SCHEMA_NAME(s.[schema_id]) IN (?)
ORDER BY [schema_name], [object_name]
