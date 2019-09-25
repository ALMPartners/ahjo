/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    TABLE_SCHEMA
    ,TABLE_NAME
    ,COLUMN_NAME
    ,g.[Extended property]
    ,g.meta_name 
FROM  INFORMATION_SCHEMA.COLUMNS 
LEFT JOIN ( SELECT 
                S.name AS [Schema Name]
                ,O.name AS [Object Name]
                ,c.name AS [Column name]
                ,EP.name
                ,CONVERT(varchar(200),EP.value) AS [Extended property]
                ,CONVERT(varchar(200), EP.name) AS meta_name 
            FROM sys.extended_properties EP 
            INNER JOIN sys.all_objects O ON EP.major_id = O.object_id 
            INNER JOIN sys.schemas S on O.schema_id = S.schema_id 
            INNER JOIN sys.columns AS c ON EP.major_id = c.object_id AND EP.minor_id = c.column_id) AS g 
ON g.[Schema Name] = TABLE_SCHEMA AND g.[Object Name] = TABLE_NAME AND g.[Column name] = COLUMN_NAME 
WHERE TABLE_SCHEMA IN (?)
ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME