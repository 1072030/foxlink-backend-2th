# Foxlink API Backend

## Prerequisite
1. Python 3.8+
2. Docker
3. Mypy linter (Recommend, for development use)

## How to Start?(Production)
1. Download this repo's files as a zip.
2. Uncompress the zip to a destination.
3. Edit **docker-compose.yaml** and enviroment file to update server configs.
4. Type `bash scripts/build.sh` in project's directory to start up the servers meanwhile initialize the required database tables.

## How to Start?(Development)
1. Download this repo's files as a zip.
2. Uncompress the backend project to a destination.
3. Download the testing environment as a zip.
4. Uncompress the testing project to a destination.
5. Edit the **.env**  file for the desire development settings.
6. Build the server with scripts in the testing project to start up the development server (**incubator**).

# Related Infos
- Server Settings:
  - Frontend Broker Website: 140.118.127.134:8086
  - API Server Docs: http://140.118.127.134:80/docs
    - Default Account:
      - username: admin
      - password: foxlink
- EasyConnect(VPN) Setting:
  - URL: https://dkvpn.foxlink.com.tw:4433/
  - Username: cbgtw
  - Password: foxlink3##
  - Server IP: 192.168.65.210
  - Server User:root
- Factory SSH Setting:
  - Server IP: 192.168.65.210
  - Username: ntust
  - Password: aa946809
  - Port:22
  - --本地密碼--
  - Username: root
  - Password: aa946809
- Device DataBase Setting:
  - Server IP: 172.168.1.231 , 172.168.1.237
  - Username: ntust
  - Password: ntustpwd
  - Port: 3306
- Factory DataBase Settings:
  - 第九車間
    - Server IP: 172.168.1.180
    - Username : root
    - password: AqqhQ993VNto
    - Port: 27000
  - 第十車間
    - Server IP : 172.168.1.180
    - Username : root
    - password: AqqhQ993VNto
    - Port: 27001
