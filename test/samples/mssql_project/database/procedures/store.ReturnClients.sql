IF OBJECT_ID('store.ReturnClients', 'P') IS NOT NULL
    DROP PROCEDURE [store].[ReturnClients]
GO

CREATE PROCEDURE [store].[ReturnClients]
AS
-- return all clients
SELECT * FROM store.Clients;
