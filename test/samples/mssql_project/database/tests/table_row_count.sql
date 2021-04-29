SELECT 
	'Clients' AS [Table name],
	COUNT(*) AS [Row count]
FROM $(DB_NAME).store.Clients
UNION ALL
SELECT 
	'Products' AS [Table name],
	COUNT(*) AS [Row count]
FROM $(DB_NAME).store.Products
