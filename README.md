# J4U-Server
Server for the "Jobs For You" project.

Installing the application
pip3 install -r requirements.txt

Running the application
python3 server.py
docker run -p 3306:3306 --name j4u-mysql -e MYSQL_ROOT_PASSWORD=my-secret-pw -e MYSQL_DATABASE=j4u -d mysql:5.7

Troubleshooting
docker restart j4u-mysql