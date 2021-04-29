-- There is no NOCOUNT ON
-- Hence this won't return any rows for execute_from_file

DECLARE @RESULT as TABLE (QUESTION varchar(255), ANSWER varchar(10))

IF (
    SELECT COUNT(*)
    FROM store.Products
    ) > 0
 INSERT INTO @RESULT (QUESTION, ANSWER) SELECT 'Is Products Populated?','YES' as RESULT
 ELSE 
 INSERT INTO @RESULT (QUESTION, ANSWER) SELECT 'Is Products Populated?','NO' as RESULT


 -- PRINT RESULTS
SELECT *
FROM @RESULT

--SET NOCOUNT OFF
