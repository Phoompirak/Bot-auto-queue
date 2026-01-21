#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Install Chrome
STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
  mkdir -p ./chrome-bin
  rpm2cpio ./google-chrome-stable_current_x86_64.rpm | cpio -idmv -D ./chrome-bin
  echo "...Chrome Installed"
else
  echo "...Chrome already installed"
fi

# Add Chrome to PATH
export PATH=$PATH:$STORAGE_DIR/chrome/chrome-bin/usr/bin
export CHROME_BIN=$STORAGE_DIR/chrome/chrome-bin/usr/bin/google-chrome-stable
