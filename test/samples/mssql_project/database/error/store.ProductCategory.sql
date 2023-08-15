-- name field is NULL and will cause an error

SET XACT_ABORT ON
SET NOCOUNT ON

SET IDENTITY_INSERT [store].[ProductCategory] ON 

INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (7, N'Rieskat', N'Rieskaleivät')
GO
INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (8, NULL, NULL)
GO
INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (9, N'Sämpylät', N'Sämpyläleivät')
GO

SET IDENTITY_INSERT [store].[ProductCategory] OFF
