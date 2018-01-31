#!/bin/bash

cd container;
zip -r lambda_code.zip *;
cd ../;
aws lambda update-function-code --zip-file fileb://container/lambda_code.zip --function-name ${LAMBDA_NAME};
rm container/lambda_code.zip;
