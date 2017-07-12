#!/bin/bash

if [ ! -d inst_EXE ]; then
    echo "You must first deploy the Windows version"
    exit 1
fi

if [ -e releases/gmail-backup-$1 ]; then
    rm -rf releases/gmail-backup-$1
fi

if [ -e releases/gmail-backup-$1-linux ]; then
    rm -rf releases/gmail-backup-$1-linux
fi


mv inst_EXE releases/gmail-backup-$1
mv releases/gmail-backup-$1/gmail-backup-installer.exe releases/gmail-backup-$1/gmail-backup-$1.exe 
./setup.sh
mv dist_SH releases/gmail-backup-$1-linux

if [ -e ~/tmp/gmail-backup-$1.zip ]; then
    rm ~/tmp/gmail-backup-$1.zip 
fi

if [ -e ~/tmp/gmail-backup-$1-linux.zip ]; then
    rm ~/tmp/gmail-backup-$1-linux.zip 
fi

svn copy . svn+ssh://uk506p01-kky.fav.zcu.cz/svn/projects/gmail-backup/branches/gmail-backup-$1 -m "Deployed version $1 of GMail Backup"

cd releases

cp gmail-backup-$1/gmail-backup-$1.exe ~/tmp/
zip -9r ~/tmp/gmail-backup-$1-linux.zip gmail-backup-$1-linux

