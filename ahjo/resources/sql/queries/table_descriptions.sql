/** 
# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0
*/

SELECT 
    s.TABLE_SCHEMA
    ,s.TABLE_NAME
    ,CONVERT(varchar(200), e.value) as value
    ,CONVERT(varchar(200), e.name) as meta_name
FROM INFORMATION_SCHEMA.TABLES AS s 
    LEFT JOIN sys.extended_properties AS e on e.major_id = OBJECT_ID('' + s.TABLE_SCHEMA + '.' + s.TABLE_NAME) AND minor_id = 0 
WHERE s.TABLE_TYPE='BASE TABLE' AND s.TABLE_SCHEMA in (?)
ORDER BY s.TABLE_SCHEMA, s.TABLE_NAME, e.value