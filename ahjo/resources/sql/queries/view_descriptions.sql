/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    SCHEMA_NAME(s.schema_id) as SCHEMA_NAME
    ,s.name as view_name
    ,CONVERT(varchar(200), e.value) as value
    ,CONVERT(varchar(200), e.name) as meta_name 
FROM sys.views as s 
    LEFT JOIN sys.extended_properties AS e ON e.major_id = s.object_id AND minor_id = 0 
WHERE SCHEMA_NAME(s.schema_id) in (?)
ORDER BY SCHEMA_NAME, view_name