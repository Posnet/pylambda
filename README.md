## This repo contains a custom lambda runtime.
Please read [https://www.denialof.services/lambda/](https://www.denialof.services/lambda/) for details of how it works.

But the short summary is that is uses module loading to take control of the AWS Lambda runtime before replacing it with a python version written from scratch to match the unspecified AWS API.

Note there is no reason to use this runtime directly, it is incomplete, slower and more error prone than the normal python runtime. 

It is purely a learning experiment, and can server as a base for writing more performant more flexible runtimes than those that are provided natively by AWS Lambda.

### copy to .envrc and use direnv
for example:
```
layout python
export LAMBDA_NAME=pyinject
export LAMBDA_ROLE=arn:aws:iam::12345678910:role/service-role/lambda-execution-role
```

### Project scripts

`create.sh` -> creates the initial Lambda function, should only need to be run once

`load.sh` -> uploads the current source to the Lambda function

`save.sh` -> downloads the contents of the Lambda function to the current dir and commits it (useful if you've been editing the function in the AWS console)

`run.sh`  -> execute the function and print the result. (You will need to view the Lambda CloudWatch logs separately)

`toggle.sh` -> this toggles the Lambda custom runtime injection. It does this by setting and unsetting the `PYTHONPATH` environment variable. This works because the custom runtime relies on setting the `PYTHONPATH` environment variable to control python module loading and gain control of the container execution from the normal runtime.

