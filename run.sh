#!/bin/bash
aws lambda invoke --function-name $LAMBDA_NAME out.json > /dev/null
cat out.json
rm out.json
