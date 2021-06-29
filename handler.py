import json
import boto3
import datetime

f = open("config.json", "r")
configDict = json.loads(f.read())
f.close()

supportedRegions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1"]

def ec2GetInstanceTypes(regionName):
    
    ec2Client = boto3.client('ec2', region_name=regionName)   
    
    return ec2Client.describe_instance_types()

def ec2StopInstances(regionName, instanceId):

    ec2Client = boto3.client('ec2', region_name=regionName)   

    ec2StopInstanceResponse = ec2Client.stop_instances(
        InstanceIds=[
            instanceId,
        ],
        Hibernate=False,
        DryRun=False
    )

    print(str(ec2StopInstanceResponse))

    return ec2StopInstanceResponse

def ec2DescribeInstances(regionName, instanceId=None):

    ec2Client = boto3.client('ec2', region_name=regionName)

    ec2DescribeInstancesResponse = None

    if instanceId:
        print("\nGetting instance " + instanceId + " in " + regionName + " ...")
        ec2DescribeInstancesResponse = ec2Client.describe_instances(
            InstanceIds=[
                instanceId,
            ]
        )
    else:
        print("\nGetting all instances in " + regionName + " ...")
        ec2DescribeInstancesResponse = ec2Client.describe_instances()

    return ec2DescribeInstancesResponse

def filterInstancesByTags(regionName, instanceId):

    # ec2DescribeInstancesResponse = ec2DescribeInstances(regionName, instanceId)

    resourceExceptionFlag = False

    for tags in instanceId["Tags"]:
        if configDict["exceptionTag"]["keyName"].lower() in str(tags["Key"]).lower():
            resourceExceptionFlag = True
            
    return not resourceExceptionFlag

def getInstanceMetricStats(regionName, instanceId, startTime, endTime):

    cloudwatchClient = boto3.client('cloudwatch')

    getInstanceMetricsResponse = cloudwatchClient.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'metricDataRequest',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/EC2',
                        'MetricName': 'CPUUtilization',
                        'Dimensions': [
                            {
                                'Name': 'InstanceId',
                                'Value': 'i-057b204c319a4b2ac'
                            }
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Average',
                    'Unit': 'Percent'
                },
                'Label': 'CPUUtilization',
                'ReturnData': True
            },
        ],
        StartTime="2021-06-27T22:48:00",
        EndTime="2021-06-28T22:53:00"
    )

    print(str(getInstanceMetricsResponse["MetricDataResults"]))

    # getInstanceMetricStatsResponse = cloudwatchClient.get_metric_statistics(
    #     Namespace='AWS/EC2',
    #     MetricName='CPUUtilization',
    #     Dimensions=[
    #         {
    #             'Name': 'InstanceId',
    #             'Value': 'i-057b204c319a4b2ac'
    #         },
    #     ],
    #     StartTime=startTime,
    #     EndTime=endTime,
    #     Period=300,
    #     Statistics=[
    #         'Average',
    #     ],
    #     Unit='Percent'
    # )
    
    # print(str(getInstanceMetricStatsResponse))

    # listMetricsResponse =  cloudwatchClient.list_metrics(
    #     Namespace='AWS/EC2',
    #     MetricName='CPUUtilization',
    #     Dimensions=[
    #         {
    #             'Name': 'InstanceId',
    #             'Value': str(instanceId)
    #         },
    #     ]
    # )

    # print(str(listMetricsResponse))

def main(event, context):

    startTime = (datetime.datetime.now() - datetime.timedelta(days=1)) # (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
    endTime = datetime.datetime.now() # datetime.datetime.now().isoformat()

    # aws cloudwatch get-metric-statistics --metric-name CPUUtilization --start-time 2021-06-27T22:48:00 --end-time 2021-06-28T22:53:00 --period 300 --namespace AWS/EC2 --statistics Average --dimensions Name=InstanceId,Value=i-057b204c319a4b2ac

    print((datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"))
    print(str(type(startTime)))
    print(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    print(str(type(endTime)))

    for regionName in supportedRegions:
        
        print("\nAWS Region " + str(regionName))
        ec2DescribeInstancesResponse = ec2DescribeInstances(regionName)

        for instance in ec2DescribeInstancesResponse["Reservations"]:

            if filterInstancesByTags(regionName, instance["Instances"][0]):

                print("\nInstance Id - " + str(instance["Instances"][0]["InstanceId"]))
                getInstanceMetricStats(regionName, instance["Instances"][0]["InstanceId"], startTime, endTime)
