#!/bin/bash
aws lambda invoke --function-name $LAMBDA_NAME --client-context 'eyJmb28iOiJiYXIifQ==' out.json > /dev/null
cat out.json
rm out.json
