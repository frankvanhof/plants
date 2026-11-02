#!/bin/bash

PI_USER="frank"
PI_HOST="192.168.1.60"
PI_PORT="615"
TARGET_DIR="/home/frank/plants"

echo "🚀 Code en data synchroniseren naar tijdelijke map op de Raspberry Pi..."
rsync -avz -e "ssh -p $PI_PORT" --exclude '.git' --exclude '__pycache__' ./ $PI_USER@$PI_HOST:~/plants_deploy_tmp/

echo "🔧 Rechten goedzetten en verplaatsen naar definitieve locatie..."
ssh -p $PI_PORT -t $PI_USER@$PI_HOST "mkdir -p $TARGET_DIR && \
                          rsync -av ~/plants_deploy_tmp/ $TARGET_DIR/ && \
                          chmod +x $TARGET_DIR/*.py && \
                          rm -rf ~/plants_deploy_tmp/"
                          
echo "✅ Deployment succesvol afgerond!"
