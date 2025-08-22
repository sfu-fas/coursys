#!/usr/bin/env python3

# Likely usage:
# ./manage.py dbdump --filename - | ./tools/dbdump_split.py

# Then to restore most of the database:
# pv dbdump.sql | ./manage.py dbshell
# System should now be in a working state. Then at your leisure, restore the request log:
# pv requestlog.sql | ./manage.py dbshell


import re
import sys

start_inserts = re.compile(r'^LOCK TABLES `log_requestlog` WRITE')
end_inserts = re.compile(r'^UNLOCK TABLES')
in_requestlog = False

dump = open('dbdump.sql', 'w')
logdump = open('requestlog.sql', 'w')


for line in sys.stdin:
    if start_inserts.match(line):
        in_requestlog = True
    elif in_requestlog and end_inserts.match(line):
        in_requestlog = False
    
    # logic here implicitly drops the LOCK and UNLOCK lines around the log_requestlog table inserts

    elif in_requestlog:
        logdump.write(line)
    else:
        dump.write(line)
    

'''
# Note for testing to drop all tables in a dev environment from https://stackoverflow.com/a/12917793

DROP PROCEDURE IF EXISTS `drop_all_tables`;

DELIMITER $$
CREATE PROCEDURE `drop_all_tables`()
BEGIN
    DECLARE _done INT DEFAULT FALSE;
    DECLARE _tableName VARCHAR(255);
    DECLARE _cursor CURSOR FOR
        SELECT table_name 
        FROM information_schema.TABLES
        WHERE table_schema = SCHEMA();
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET _done = TRUE;

    SET FOREIGN_KEY_CHECKS = 0;

    OPEN _cursor;

    REPEAT FETCH _cursor INTO _tableName;

    IF NOT _done THEN
        SET @stmt_sql = CONCAT('DROP TABLE IF EXISTS `', _tableName, '`');
        PREPARE stmt1 FROM @stmt_sql;
        EXECUTE stmt1;
        DEALLOCATE PREPARE stmt1;
    END IF;

    UNTIL _done END REPEAT;

    CLOSE _cursor;
    SET FOREIGN_KEY_CHECKS = 1;
END$$

DELIMITER ;

call drop_all_tables(); 

DROP PROCEDURE IF EXISTS `drop_all_tables`;

SHOW TABLES;
'''