#!/bin/bash
echo "def handler(msg, ctx):
    return True" > handler.py;
zip -r lambda_code.zip handler.py;
aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --role $LAMBDA_ROLE \
    --runtime python3.6 \
    --handler "handler.handler" \
    --zip-file fileb://lambda_code.zip \
    --timeout 3 \
    --memory 1024;
rm handler.py lambda_code.zip;
