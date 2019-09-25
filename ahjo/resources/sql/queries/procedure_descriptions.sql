/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    SCHEMA_NAME(s.schema_id) as SCHEMA_NAME
    ,s.name as proc_name
    ,CONVERT(varchar(200), e.value) as value
    ,CONVERT(varchar(200), e.name) as meta_name 
FROM sys.procedures as s 
    LEFT JOIN sys.extended_properties AS e on e.major_id = s.object_id 
WHERE SCHEMA_NAME(s.schema_id) in (?)
ORDER BY SCHEMA_NAME, proc_name