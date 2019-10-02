/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    SCHEMA_NAME(s.[schema_id]) AS [schema_name]
    ,s.[name] AS [func_name]
    ,CONVERT(VARCHAR(200), e.[value]) AS [value]
    ,CONVERT(VARCHAR(200), e.[name]) AS [meta_name]
    ,'function' AS [object_type]
FROM sys.objects AS s 
    LEFT JOIN sys.extended_properties AS e 
		ON e.[major_id] = s.[object_id]
WHERE SCHEMA_NAME(s.[schema_id]) IN (?)
	AND s.[type] IN ('FN', 'IF', 'FN', 'AF', 'FS', 'FT') 
ORDER BY [schema_name], [func_name]