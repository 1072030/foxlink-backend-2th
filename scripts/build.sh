bash scripts/servers.sh rebuild
sleep 15
docker compose exec foxlink-backend bash scripts/rebuild_database.sh