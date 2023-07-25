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


# MQTT Topics
- foxlink/users/{username}/missions
1. 當收到新任務時
```jsonc
{
  "type" : "new", // 該事件的類別：new 為新增任務
  "mission_id" : 12, // 新增任務的 ID
  "device" : {
    "project" : "n104",
    "process" : "M3段",
    "line" : 4,
    "name" : "Device_11"
  },
  "name": "任務名稱",
  "description": "任務的敘述",
  "events": [
    "category" : 190, // 該故障的分類編號
    "message" : "进料打码站故障", // 故障資訊
    "done_verified" : false, // 該故障是否維修完畢
    "event_beg_date" : "2022-04-23T07:09:22", // 該故障出現時間
    "event_end_date" : null
  ]
}
```
2. 當下屬標記某個任務為緊急任務時，系統通知上屬
```jsonc
{
  "type" : "emergency",
  "mission_id" : 12, // 緊急任務的 ID
  "device" : {
    "project" : "n104",
    "process" : "M3段",
    "line" : 4,
    "name" : "Device_11"
  },
  "name": "任務名稱",
  "description": "任務的敘述",
  "worker": {
    "username": "員工 ID",
    "full_name": "員工姓名"
  },
  "events": [
    "category" : 190, // 該故障的分類編號
    "message" : "进料打码站故障", // 故障資訊
    "done_verified" : false, // 該故障是否維修完畢
    "event_beg_date" : "2022-04-23T07:09:22", // 該故障出現時間
    "event_end_date" : null
  ]
}
```
- foxlink/users/{username}/move-rescue-station - 當完成任務後，系統通知前往救援站待命時
```jsonc
{
  "type": "rescue",
  "mission_id": 1, // 前往救援站任務 ID
  "name": "任務名稱",
  "description": "任務的敘述",
  "rescue_station": "要前往的救援站 ID"
}
```
- foxlink/{車間名稱}/mission/rejected - 當有任務被拒絕超過兩次，會觸發這一事件
```jsonc
{
    "id": 1, // 被拒絕超過兩次的任務 ID
    "worker": "string", // 員工姓名
    "rejected_count": 2 // 該任務總共被拒絕了幾次
}
```
- foxlink/{車間名稱}/no-available-worker - 當有任務無人可以指派時，會推送這個訊息
```jsonc
{
  "mission_id" : 1, // 無人可供指派的任務 ID
  // Device 詳細資訊
  "device" : {
    "device_id" : "D53@1@Device_9",
    "device_name" : "Device_9",
    "project" : "D53",
    "process" : "M3段",
    "line" : 1
  },
  "name" : "D53@1@Device_9 故障", // 任務名稱
  "description" : "", // 該任務的敘述
  "assignees" : [ ],
  // 該任務的 Device 所受影響的故障列表
  "events" : [ {
    "category" : 190,
    "message" : "进料打码站故障",
    "done_verified" : false, // 該故障是否維修完畢
    "event_beg_date" : "2022-04-23T07:09:22", // 該故障出現時間
    "event_end_date" : null
  } ],
  "is_started" : false,
  "is_closed" : false,
  "created_date" : "2022-04-23T07:12:31",
  "updated_date" : "2022-04-23T07:12:31"
}
```
- foxlink/users/{username}/subordinate-rejected - 當天如果有下屬拒絕任務兩次以上，就會推送這則訊息
```jsonc
{
    "subordinate_id": '145287', // 下屬的 ID
    "subordinate_name": 'string', // 下屬姓名
    "total_rejected_count": 2 // 下屬當日總拒絕次數
}
```
- foxlink/users/{username}/mission-overtime - 當有任務處理時長超過門檻值，系統會通知處理員工之上級
```jsonc
{
    "mission_id": 0, // 任務 ID
    "mission_name": "string", // 任務名稱
    "worker_id": "145287", // 處理員工 ID
    "worker_name": "string", // 處理員工姓名
    "duration": 0, // 目前處理時長（秒）
},
```
- （當前停用）foxlink/users/{username}/worker-unusual-offline - 當員工異常離線時（網路不佳），超過某特定時間，將會通知該員工上級。
```jsonc
{
  "worker_id": "rescue@第九車間@1", // 異常離線的員工 ID
  "worker_name": "string", // 員工姓名
}
```
- foxlink/users/{username}/connected - 當有其他裝置登入使用者帳號時
```jsonc
{
  "connected": true
}
```
- foxlink/users/{username}/overtime-duty - 通知員工超過換班時間工作，
```jsonc
{"message": "因為您超時工作，所以您目前的任務已被移除。"}
```

# Server Config
| Config Name                            | Description                                                                          | Default Value                | Example Value                |
| -------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------- | ---------------------------- |
| DATABASE_HOST                          | API's Database IP/Name                                                               | None                         | 127.0.0.1                    |
| DATABASE_PORT                          | API's Database Port                                                                  | None                         | 27001                        |
| DATABASE_USER                          | API's Database User                                                                  | None                         | root                         |
| DATABASE_PASSWORD                      | API's Database Password                                                              | None                         | AqqhQ993VNto                 |
| DATABASE_NAME                          | API's Database Name                                                                  | None                         | foxlink                      |
| PY_ENV                                 | Project Mode("dev","product"), Decides whether to include the testing routes         | dev                          | dev                          |
| FOXLINK_EVENT_DB_HOSTS                 | Event Databases IP/Name:Port                                                         | None                         | ["127.0.0.1:27001"]          |
| FOXLINK_EVENT_DB_USER                  | Event Databases User                                                                 | None                         | root                         |
| FOXLINK_EVENT_DB_PWD                   | Event Databases Password                                                             | None                         | AqqhQ993VNto                 |
| FOXLINK_EVENT_DB_NAME                  | Event Databases Name                                                                 | None                         | aoi                          |
| FOXLINK_EVENT_DB_TABLE_POSTFIX         | Event Databases Target Postfix                                                       | None                         | _event_new                   |
| FOXLINK_DEVICE_DB_HOST                 | Device Info Database IP:Port                                                         | None                         | 127.0.0.1:27001              |
| FOXLINK_DEVICE_DB_USER                 | Device Info Database User                                                            | None                         | root                         |
| FOXLINK_DEVICE_DB_PWD                  | Device Info Database Password                                                        | None                         | AqqhQ993VNto                 |
| FOXLINK_DEVICE_DB_NAME                 | Device Info Database Name                                                            | None                         | sfc                          |
| JWT_SECRET                             | The secret generating the JWT tokens                                                 | secret                       | secret                       |
| MQTT_BROKER                            | MQTT Server IP/Name                                                                  | None                         | 127.0.0.1                    |
| MQTT_PORT                              | MQTT Server Port                                                                     | None                         | 1883                         |
| EMQX_USERNAME                          | MQTT Server Username                                                                 | admin                        | admin                        |
| EMQX_PASSWORD                          | MQTT Server Password                                                                 | public                       | public                       |
| WORKER_REJECT_AMOUNT_NOTIFY            | Amount of Mission Rejections to Notify the Worker's Superior                         | 2                            | 2                            |
| MISSION_REJECT_AMOUT_NOTIFY            | Amount of Worker Rejections to Notify the Mission's Workshop Managers                | 2                            | 2                            |
| DAY_SHIFT_BEGIN                        | Begin Time of the Day Shift                                                          | 07:40                        | 07:40                        |
| DAY_SHIFT_END                          | End Time of the Day Shift                                                            | 19:40                        | 19:40                        |
| MAX_NOT_ALIVE_TIME                     | (Depricated)                                                                         | None                         | None                         |
| MISSION_ASSIGN_OT_MINUTES              | Overtime of the Mission Assigned to Worker before Being Canceled                     | 10                           | 10                           |
| WORKER_IDLE_OT_RESCUE_MINUTES          | Overtime of the Worker Being Idle before Making the Worker Return to a Rescue Device | 1                            | 1                            |
| MISSION_WORK_OT_NOTIFY_PYRAMID_MINUTES | Overtime of the Worker Working on a Mission                                          | [20,30,30]                   | [20,30,30]                   |
| RECENT_EVENT_PAST_DAYS                 | (Depricated)                                                                         | None                         | None                         |
| DISABLE_FOXLINK_DISPATCH               | Disabling the Mission Dispatch Routine                                               | 0(False)                     | 1(True)                      |
| DISABLE_STARTUP_RESCUE_MISSION         | Disabling the Startup Mission Routine                                                | 0(False)                     | 1(True)                      |
| PWD_SCHEMA                             | Password Hashing Schema                                                              | sha256_crypt                 | bcrypt                       |
| PWD_SALT                               | Passworkd Hashing Salt                                                               | F0XL1NKPWDHaSH               | hashsalt                     |
| DEBUG                                  | Debug Mode: Switch on the debug messages and use different event synchronize method  | 0(False)                     | 1(True)                      |
| TZ                                     | Time Zone                                                                            | pytz.timezone("Asia/Taipei") | pytz.timezone("Asia/Taipei") |


# Related Infos
- Server Settings:
  - MQTT Broker Website: 140.118.127.134:18083
  - Frontend Broker Website: 140.118.127.134:8086
  - API Server Docs: http://140.118.127.134:80/docs
    - Default Account:
      - username: admin
      - password: foxlink
- EasyConnect(VPN) Setting:
  - URL: https://dkvpn.foxlink.com.tw:4433
  - Username: cbgtw
  - Password: aA946809@
  - Server IP: 192.168.65.210
  - Server User:root
  - Server Ports: 80,3306,8083,18083,27010
- Factory SSH Setting:
  - Server IP: 192.168.65.210
  - Username: ntust
  - Password: aa946809
  - Port:22
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
