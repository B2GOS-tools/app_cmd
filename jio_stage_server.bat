python setup.py develop
echo start
python app_cmd.py setsettings "apps.serviceCenterUrl=https://api.jio.kaiostech.com/v2.0"
python app_cmd.py setsettings "deviceinfo.cu=4044O-2BAQUS1-R"
python app_cmd.py setpref "apps.serviceCenter.devOrigins=https://api.test.kaiostech.com,https://api.stage.kaiostech.com,https://storage.test.kaiostech.com,https://storage.stage.kaiostech.com,http://storage.test.kaiostech.com,http://storage.stage.kaiostech.com,https://api.jio.kaiostech.com,https://storage.jio.kaiostech.com"

