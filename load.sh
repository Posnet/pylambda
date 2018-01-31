#!/bin/bash

zip -r lambda_code.zip container/*
aws lambda update-function-code --zip-file fileb://lambda_code.zip --function-name ${LAMBDA_NAME}
rm lambda_code.zip
