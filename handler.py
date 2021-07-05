import json
import boto3
import os
import datetime

from botocore.exceptions import MissingParametersError

f = open("config.json", "r")
configDict = json.loads(f.read())
f.close()

supportedRegions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1"]

def ec2GetInstanceTypes(regionName):
    
    ec2Client = boto3.client('ec2', region_name=regionName)   
    
    return ec2Client.describe_instance_types()

def ec2StopInstances(regionName, instance):

    ec2Client = boto3.client('ec2', region_name=regionName)  

    if instance["HibernationOptions"]["Configured"]:
        print("\nInstance hibernation supported. Hibernating instance " + instance["InstanceId"] + " ...")
    else:
        print("\nStopping instance " + instance["InstanceId"] + " ...")

    stopTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    ec2StopInstanceResponse = ec2Client.stop_instances(
        InstanceIds=[
            instance["InstanceId"],
        ],
        Hibernate=instance["HibernationOptions"]["Configured"],
        DryRun=False
    )

    print(str(ec2StopInstanceResponse))

    ec2TagInstance(regionName, instance["InstanceId"], stopTime)

def ec2TagInstance(regionName, instanceId, actionTime):

    ec2Client = boto3.client('ec2', region_name=regionName)

    ec2TagInstanceResponse = ec2Client.create_tags(        
        Resources=[
            instanceId,
        ],
        Tags=[
            {
                'Key': 'StoppedBy',
                'Value': 'aws-cost-optimization-remediate/prod/us-west-2'
            },
            {
                'Key': 'StoppedTime',
                'Value': actionTime
            }
        ]
    )

    print(str(ec2TagInstanceResponse))

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
        print("\nGetting all running instances in " + regionName + " ...")
        ec2DescribeInstancesResponse = ec2Client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running'
                    ]
                }
            ]
        )

    return ec2DescribeInstancesResponse

def filterInstancesByTags(instance):    

    resourceExceptionFlag = False

    for tags in instance["Tags"]:
        if configDict["exceptionTag"]["keyName"].lower() in str(tags["Key"]).lower():
            resourceExceptionFlag = True
            
    return not resourceExceptionFlag

def getInstanceMetricStats(regionName, instanceId, minThresholdCpuUtilPercent, startTime, endTime):

    cloudwatchClient = boto3.client('cloudwatch', region_name=regionName)  

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
                                'Value': instanceId
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
        StartTime=startTime,
        EndTime=endTime
    )

    averageUsagePercent = sum(getInstanceMetricsResponse["MetricDataResults"][0]["Values"])/len(getInstanceMetricsResponse["MetricDataResults"][0]["Values"])

    print("\nAverage CPU Utilization is " + " below " if averageUsagePercent < minThresholdCpuUtilPercent else " above " + minThresholdCpuUtilPercent + "% - " + str(averageUsagePercent))

    if averageUsagePercent < float(minThresholdCpuUtilPercent):
        return True

    return False

def main(event, context):

    minThresholdCpuUtilPercent = os.environ.get("minThresholdCpuUtilizationPercentage")
    startTime = (datetime.datetime.now() - datetime.timedelta(hours=4))
    endTime = datetime.datetime.now()

    for regionName in supportedRegions:
        
        print("\nAWS Region " + str(regionName))
        ec2DescribeInstancesResponse = ec2DescribeInstances(regionName)

        for instance in ec2DescribeInstancesResponse["Reservations"]:

            if filterInstancesByTags(instance["Instances"][0]):

                print("\nInstance Id - " + str(instance["Instances"][0]["InstanceId"]))
                
                if getInstanceMetricStats(regionName, instance["Instances"][0]["InstanceId"], minThresholdCpuUtilPercent, startTime, endTime):

                    ec2StopInstances(regionName, instance["Instances"][0])