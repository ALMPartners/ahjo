SET IDENTITY_INSERT [store].[ProductCategory] ON 

INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (4, N'Vehnäleivät', N'Vehnästä valmistetut leivät')
GO
INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (5, N'Ohraleivät', N'Ohrasta valmistetut leivät')
GO
INSERT [store].[ProductCategory] ([id], [name], [description]) VALUES (6, N'Näkkileivät', N'Näkkileivät')
GO

SET IDENTITY_INSERT [store].[ProductCategory] OFF
