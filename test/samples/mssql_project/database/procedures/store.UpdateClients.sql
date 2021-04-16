SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

IF OBJECT_ID('store.UpdateClients', 'P') IS NOT NULL
    DROP PROCEDURE [store].[UpdateClients]
GO

CREATE PROCEDURE [store].[UpdateClients]
AS
-- return all clients
UPDATE store.Clients
SET phone = 0401234567
