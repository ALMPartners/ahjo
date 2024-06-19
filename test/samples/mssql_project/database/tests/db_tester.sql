SET NOCOUNT ON

DECLARE @ISSUE varchar(10)
DECLARE @TEST_NAME varchar(70)
DECLARE @RESULTS as TABLE (start_time datetime, end_time datetime, test_name varchar(255), issue varchar(10), result varchar(10))
DECLARE @RESULT varchar(10)
DECLARE @START_TIME datetime = GETDATE()
-----------------------------------------

SET @ISSUE = 'ISSUE-1'
SET @TEST_NAME = 'TEST-1'
SET @START_TIME = GETDATE()
SET @RESULT = 'OK'
INSERT INTO @RESULTS (start_time, end_time, test_name, issue, result) VALUES (@START_TIME, GETDATE(), @TEST_NAME, @ISSUE, @RESULT)

-----------------------------------------

SET @ISSUE = 'ISSUE-2'
SET @TEST_NAME = 'TEST-2'
SET @START_TIME = GETDATE()
SET @RESULT = 'Failed'
INSERT INTO @RESULTS (start_time, end_time, test_name, issue, result) VALUES (@START_TIME, GETDATE(), @TEST_NAME, @ISSUE, @RESULT)

-----------------------------------------

SET @ISSUE = 'ISSUE-3'
SET @TEST_NAME = 'TEST-3'
SET @START_TIME = GETDATE()
SET @RESULT = 'OK'
INSERT INTO @RESULTS (start_time, end_time, test_name, issue, result) VALUES (@START_TIME, GETDATE(), @TEST_NAME, @ISSUE, @RESULT)

-----------------------------------------

 -- OUTPUT RESULTS
SELECT *
FROM @RESULTS