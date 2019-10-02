/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    c.[TABLE_SCHEMA] AS [schema_name]
    ,c.[TABLE_NAME] AS [object_name]
    ,c.[COLUMN_NAME] AS [column_name]
    ,g.[value] AS [value]
    ,g.[meta_name] AS [meta_name]
	,CASE g.[object_type] 
		WHEN 'V' THEN 'view'
		ELSE 'table' 
	END AS [object_type]
FROM  INFORMATION_SCHEMA.COLUMNS AS c 
LEFT JOIN 
		(SELECT 
			S.[name] AS [schema_name]
			,O.[name] AS [object_name]
			,C.[name] AS [column_name]
			,O.type AS [object_type]
			,CONVERT(VARCHAR(200),EP.[value]) AS [value]
			,CONVERT(VARCHAR(200), EP.[name]) AS [meta_name]
		FROM sys.all_objects AS O
			INNER JOIN sys.schemas AS S 
				ON O.[schema_id] = S.[schema_id]
			INNER JOIN sys.columns AS C 
				ON O.[object_id] = C.[object_id]
			LEFT JOIN sys.extended_properties AS EP
				ON EP.[major_id] = O.[object_id] AND EP.[minor_id] = C.[column_id]) AS g
	ON g.[schema_name] = c.[TABLE_SCHEMA] 
	AND g.[object_name] = c.[TABLE_NAME] 
	AND g.[column_name] = c.[COLUMN_NAME]
WHERE TABLE_SCHEMA IN (?)
ORDER BY [schema_name], [object_name], [column_name]