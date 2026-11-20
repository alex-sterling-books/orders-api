# Verification queries: Orders API 5xx

Run these yourself, in the account, so your conclusion does not rest only on the
agent's reading. Set the time range to cover at least 15 minutes before the
deploy through 15 minutes after impact ends. All times UTC.

## Logs Insights

Run in CloudWatch Logs Insights, us-east-1.

### Q1. Timeouts per minute (log group /aws/lambda/orders-submit)

```
filter @message like /Task timed out/
| stats count(*) as timeouts by bin(1m)
```

### Q2. Throttling errors that reached the function (log group /aws/lambda/orders-submit)

```
filter @message like /ProvisionedThroughputExceeded|ThrottlingException/
| stats count(*) as throttle_errors by bin(1m)
```

### Q3. Duration per minute (log group /aws/lambda/orders-submit)

```
filter @type = "REPORT"
| stats count(*) as invocations, max(@duration) as max_ms, pct(@duration, 99) as p99_ms by bin(1m)
```

### Q4. Slow inventory calls per minute (log group /aws/lambda/inventory-reserve)

```
filter @message like /"slow": true/
| stats count(*) as slow_calls by bin(1m)
```

### Q5. Successful orders by version (log group /aws/lambda/orders-submit)

```
filter event = "order_created"
| stats count(*) as orders by version, bin(1m)
```

## Metrics (AWS CLI)

Replace the times with your own window.

### M1. API Gateway 5xx and request count, one-minute periods

```
API_ID=$(aws cloudformation describe-stack-resource --stack-name orders-api \
  --logical-resource-id OrdersHttpApi --query StackResourceDetail.PhysicalResourceId --output text)

aws cloudwatch get-metric-data --region us-east-1 \
  --start-time 2026-12-08T13:55:00Z --end-time 2026-12-08T14:35:00Z \
  --metric-data-queries "[
    {\"Id\":\"e\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"AWS/ApiGateway\",\"MetricName\":\"5xx\",\"Dimensions\":[{\"Name\":\"ApiId\",\"Value\":\"$API_ID\"},{\"Name\":\"Stage\",\"Value\":\"prod\"}]},\"Period\":60,\"Stat\":\"Sum\"}},
    {\"Id\":\"c\",\"MetricStat\":{\"Metric\":{\"Namespace\":\"AWS/ApiGateway\",\"MetricName\":\"Count\",\"Dimensions\":[{\"Name\":\"ApiId\",\"Value\":\"$API_ID\"},{\"Name\":\"Stage\",\"Value\":\"prod\"}]},\"Period\":60,\"Stat\":\"Sum\"}}
  ]" --query "MetricDataResults[].{id:Id,times:Timestamps,values:Values}"
```

### M2. DynamoDB write throttling on the orders table

```
aws cloudwatch get-metric-statistics --region us-east-1 \
  --namespace AWS/DynamoDB --metric-name WriteThrottleEvents \
  --dimensions Name=TableName,Value=orders \
  --start-time 2026-12-08T13:55:00Z --end-time 2026-12-08T14:35:00Z \
  --period 60 --statistics Sum
```

### M3. The configuration that is actually live

```
aws lambda get-alias --function-name orders-submit --name live --region us-east-1
aws lambda get-function-configuration --function-name orders-submit:live \
  --region us-east-1 --query "{version:Version,timeout:Timeout,app:Environment.Variables.APP_VERSION}"
```
