#!/bin/bash
aws lambda get-function --function-name inject3 | jq '.Code.Location' | xargs -n1 wget -O 'lambda_code.zip';
unzip -o lambda_code.zip;
rm lambda_code.zip;
git add -A;
git commit -m 'autosave'

