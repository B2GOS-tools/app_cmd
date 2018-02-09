configure environment:
sudo pip install marionette-client
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate

setup dependency, make sure connect to device before this step:
python setup.py develop
python app_cmd.py


