#!/bin/bash
set_path='"/var/task"'
current_path=$(aws lambda get-function --function-name $LAMBDA_NAME | jq '.Configuration.Environment.Variables.PYTHONPATH')
if [ $current_path == $set_path ]; then
    new_path='""'
else
    new_path=$set_path;
fi

aws lambda update-function-configuration \
    --function-name $LAMBDA_NAME \
    --environment "Variables={LOG_LEVEL=DEBUG,PYTHONPATH=${new_path}}"
