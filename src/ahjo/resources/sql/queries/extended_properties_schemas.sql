/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    DISTINCT s.[name] AS [schema_name]
    ,'schema' AS [object_type]
    ,CONVERT(VARCHAR(8000), e.[name]) AS [property_name]
    ,CONVERT(VARCHAR(8000), e.[value]) AS [property_value]
FROM sys.schemas AS s 
    LEFT JOIN sys.extended_properties AS e 
        ON e.[major_id] = s.[schema_id] 
WHERE s.[name] IN (?)
ORDER BY [schema_name]