#!/bin/sh

sudo apt-get install -y python-pip python-virtualenv python-dev libsqlite3-dev libffi-dev libssl-dev
sudo apt-get install python-wxgtk2.8 python-wxtools wx2.8-doc wx2.8-examples wx2.8-headers wx2.8-i18n libjpeg-dev
# brew install phantomjs python-pyphantomjs
virtualenv env

cd env/lib/python2.7/site-packages/
ln -s /usr/lib/python2.7/dist-packages/wx-2.8-gtk2-unicode/ .
ln -s /usr/lib/python2.7/dist-packages/wx.pth .
ln -s /usr/lib/python2.7/dist-packages/wxversion.py .
ln -s /usr/lib/python2.7/dist-packages/wxversion.pyc .

cd ../../../..

env/bin/pip install -r requirements.txt

#sudo ln -s -f $(pwd)/openport-manager /etc/init.d/openport-manager
#sudo update-rc.d openport-manager defaults