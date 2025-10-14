#!/bin/bash

echo "Example job started"
#simulate a long running job
sleep 10

random_number=$((RANDOM % 10))
if [ $random_number -eq 0 ]; then
    echo "Example job failed"
    exit 1
fi
if [ $random_number -eq 1 ]; then
    echo "Example job timed out"
    exit 124
fi

echo "Example job completed"

exit 0