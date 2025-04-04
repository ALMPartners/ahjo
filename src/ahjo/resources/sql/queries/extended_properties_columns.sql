/**
# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT
    c.[TABLE_SCHEMA] AS [schema_name]
    ,c.[TABLE_NAME] AS [object_name]
    ,c.[COLUMN_NAME] AS [column_name]
	,'column' AS [object_type]
	,CASE g.[object_type]
		WHEN 'V' THEN 'view'
		ELSE 'table'
	END AS [parent_type]
    ,g.[property_name] AS [property_name]
    ,g.[property_value] AS [property_value]
FROM  INFORMATION_SCHEMA.COLUMNS AS c
LEFT JOIN
		(SELECT
			S.[name] AS [schema_name]
			,O.[name] AS [object_name]
			,C.[name] AS [column_name]
			,O.type AS [object_type]
			,CONVERT(VARCHAR(8000), EP.[value]) AS [property_value]
			,CONVERT(VARCHAR(8000), EP.[name]) AS [property_name]
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
WHERE c.[TABLE_SCHEMA] IN (?)
ORDER BY [schema_name], [object_name], [column_name]
