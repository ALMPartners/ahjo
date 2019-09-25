/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    SCHEMA_NAME(schema_id) AS 'Schema'
    ,s.name AS 'Function_name'
    ,CONVERT(varchar(200), e.value) as value
    ,CONVERT(varchar(200), e.name) as meta_name 
FROM sys.objects as s 
    LEFT JOIN sys.extended_properties AS e ON e.major_id = s.object_id 
WHERE SCHEMA_NAME(s.schema_id) in (?) AND s.type in ('FN', 'IF', 'FN', 'AF', 'FS', 'FT') 
ORDER BY SCHEMA_NAME(s.schema_id), s.name