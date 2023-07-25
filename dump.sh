HOST=127.0.0.1
PORT=27001
USER=root
DB_NAME=foxlink
MYSQL_PWD=AqqhQ993VNto
DB_BACKUP_NAME=/bk.sql
echo "Dump all DB..."
mysqldump --lock-all-tables -h $HOST -u $USER -P $PORT $DB_NAME -p$MYSQL_PWD > $DB_BACKUP_NAME

echo "Done !"
