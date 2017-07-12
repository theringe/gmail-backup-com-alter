#!/bin/bash
pygettext -o gmail-backup.pot  gmb.py gmail-backup-gui.py
for i in messages/*.po; do
    echo $i
    bn=`basename "$i"`
    i=${bn%.po}
    msgmerge -U messages/$i.po gmail-backup.pot
    mkdir -p messages/$i/LC_MESSAGES
    msgfmt messages/$i.po -o messages/$i/LC_MESSAGES/gmail-backup.mo
done
