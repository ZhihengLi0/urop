#!/bin/bash
set -e
cd /users/9/li004628/urop/snolab/presentation
python3 build_backup_pdfs.py --zips 1 4 6 7 9 10 13 15 16 18 19 22 24
for z in 1 4 6 7 9 10 13 15 16 18 19 22 24; do
  /common/software/install/migrated/libreoffice/12.05.22/libreoffice --headless \
    -env:UserInstallation=file:///tmp/claude-83979/lo_profile_batch \
    --convert-to pdf /users/9/li004628/urop/snolab/presentation/backup_galleries/_pptx/backup_zip${z}.pptx \
    --outdir /users/9/li004628/urop/snolab/presentation/backup_galleries \
    > /dev/null 2>&1 || echo "FAILED zip$z"
  echo "converted zip$z"
done
ls -la /users/9/li004628/urop/snolab/presentation/backup_galleries/*.pdf | wc -l
echo ALL DONE
