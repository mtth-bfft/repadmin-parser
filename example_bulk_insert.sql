CREATE TABLE [dbo].[repadmin_changes](
    [dn] [nvarchar](255) NOT NULL,
    [action] [varchar](20) NOT NULL,
    [attribute_name] [varchar](255) NULL,
    [attribute_value] [varchar](max) NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

BULK INSERT [repadmin_changes]
   FROM '\path\to\output\file.tsv'
   WITH
   (
      DATAFILETYPE = 'char',
      CODEPAGE = 'RAW',
      ROWS_PER_BATCH = 1,
      BATCHSIZE = 1000000,
      MAXERRORS = 10000,
      TABLOCK
   )

