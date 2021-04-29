IF OBJECT_ID('store.vwProducts', 'V') IS NOT NULL
DROP VIEW [store].[vwProducts];
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


CREATE VIEW [store].[vwProducts] 
AS

SELECT [id]
      ,[name]
      ,[category_id]
      ,[description]
      ,[unit_price]
      ,[units_in_package]
      ,[package_weight]
      ,[manufacturer]
  FROM [store].[Products]


GO
