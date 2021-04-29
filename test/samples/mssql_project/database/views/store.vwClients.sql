IF OBJECT_ID('store.vwClients', 'V') IS NOT NULL
DROP VIEW [store].[vwClients];
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


CREATE VIEW [store].[vwClients] 
AS

SELECT [id]
      ,[name]
      ,[email]
      ,[phone]
      ,[address]
      ,[zip_code]
      ,[country]
      ,[date_of_birth]
  FROM [store].[Clients]


GO
