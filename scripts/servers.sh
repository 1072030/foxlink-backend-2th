build(){
    docker compose build
}

create() {
    docker compose create
}


kill() {
    docker compose kill
}

remove() {
    kill
    docker compose rm -fs
}

start() {
    create
    docker compose start foxlink-backend
}

stop() {
    docker compose stop
}

restart(){
    kill
    remove
    start
}

rebuild(){
    kill
    remove
    build
    start
}



if [[ $1 == "start" ]];
then
    start
elif [[ $1 == "stop" ]];
then
    stop
elif [[ $1 == "remove" ]];
then
    remove
elif [[ $1 == "restart" ]];
then
    restart
elif [[ $1 == "rebuild" ]];
then
    rebuild
elif [[ $1 == "create" ]];
then
    create
else
    echo "Unknown command..."
fi
