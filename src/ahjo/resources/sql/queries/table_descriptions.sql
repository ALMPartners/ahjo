/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    s.[TABLE_SCHEMA] AS [schema_name]
    ,s.[TABLE_NAME] AS [table_name]
    ,CONVERT(VARCHAR(200), e.[value]) AS [value]
    ,CONVERT(VARCHAR(200), e.[name]) AS [meta_name]
    ,'table' AS [object_type]
FROM INFORMATION_SCHEMA.TABLES AS s 
    LEFT JOIN sys.extended_properties AS e 
		ON e.[major_id] = OBJECT_ID('' + s.[TABLE_SCHEMA] + '.' + s.[TABLE_NAME]) 
		AND e.[minor_id] = 0 
WHERE s.[TABLE_TYPE] = 'BASE TABLE' 
	AND s.[TABLE_SCHEMA] IN (?)
ORDER BY [schema_name], [table_name]