#!/bin/bash

aws lambda get-function --function-name ${LAMBDA_NAME} | jq '.Code.Location' | xargs -n1 wget -O 'lambda_code.zip';
unzip -o lambda_code.zip -d container;
rm lambda_code.zip;
git add -A;
git commit -m 'autosave';
git sync;

