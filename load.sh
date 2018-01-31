#!/bin/bash
rm lambda_code.zip
zip -r -j lambda_code.zip target/*
aws lambda update-function-code --zip-file fileb://lambda_code.zip --function-name ${LAMBDA_NAME}
