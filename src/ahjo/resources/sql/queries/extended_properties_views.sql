/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    SCHEMA_NAME(s.[schema_id]) AS [schema_name]
    ,s.[name] AS [view_name]
    ,'view' AS [object_type]
    ,CONVERT(varchar(200), e.[name]) AS [property_name]
    ,CONVERT(varchar(200), e.[value]) AS [property_value]
FROM sys.views AS s 
    LEFT JOIN sys.extended_properties AS e 
		ON e.[major_id] = s.[object_id] 
		AND e.[minor_id] = 0 
WHERE SCHEMA_NAME(s.[schema_id]) IN (?)
ORDER BY [schema_name], [view_name]