bash scripts/servers.sh rebuild
sleep 30
docker compose exec foxlink-backend bash scripts/rebuild_database.sh