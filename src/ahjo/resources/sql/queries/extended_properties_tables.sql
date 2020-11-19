/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    s.[TABLE_SCHEMA] AS [schema_name]
    ,s.[TABLE_NAME] AS [table_name]
    ,'table' AS [object_type]
    ,CONVERT(VARCHAR(8000), e.[name]) AS [property_name]
    ,CONVERT(VARCHAR(8000), e.[value]) AS [property_value]
FROM INFORMATION_SCHEMA.TABLES AS s 
    LEFT JOIN sys.extended_properties AS e 
		ON e.[major_id] = OBJECT_ID('' + s.[TABLE_SCHEMA] + '.' + s.[TABLE_NAME]) 
		AND e.[minor_id] = 0 
WHERE s.[TABLE_TYPE] = 'BASE TABLE' 
	AND s.[TABLE_SCHEMA] IN (?)
ORDER BY [schema_name], [table_name]