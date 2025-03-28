#!/bin/bash

# Install Cloudwatch agent
Invoke-WebRequest -Uri https://s3.amazonaws.com/amazoncloudwatch-agent/windows/amd64/latest/AmazonCloudWatchAgent.zip -OutFile c:\installers\AmazonCloudWatchAgent.zip
Write-Host "Extracted AmazonCloudWatchAgent.zip and setting location to c:\installers\AmazonCloudWatchAgent"


