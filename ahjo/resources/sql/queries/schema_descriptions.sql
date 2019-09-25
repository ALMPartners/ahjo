/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    distinct s.name as schema_name
    ,CONVERT(varchar(200), e.value) as value
    ,CONVERT(varchar(200), e.name) as meta_name 
FROM sys.schemas s 
    LEFT JOIN sys.extended_properties e ON e.major_id = s.schema_id 
WHERE s.name in (?)
ORDER BY schema_name