import boto3

def check_role_exists(iam_client, role_name):
    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except iam_client.exceptions.NoSuchEntityException:
        return False

def detach_policies(iam_client, role_name):
    try:
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in response['AttachedPolicies']:
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
            print(f"Detached policy: {policy['PolicyName']} from role: {role_name}")
    except Exception as e:
        print(f"Error detaching policies: {e}")

def terminate_ec2_instances(ec2_client):
    try:
        instances = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
        )
        instance_ids = [instance['InstanceId'] for reservation in instances['Reservations'] for instance in reservation['Instances']]
        
        if instance_ids:
            ec2_client.terminate_instances(InstanceIds=instance_ids)
            waiter = ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=instance_ids)
            print(f"EC2 Instances terminated: {instance_ids}")
    except Exception as e:
        print(f"Error terminating EC2 instances: {e}")

def delete_key_pair(ec2_client, key_name):
    try:
        ec2_client.delete_key_pair(KeyName=key_name)
        print(f"Deleted Key Pair: {key_name}")
    except Exception as e:
        print(f"Error deleting Key Pair: {e}")

def delete_iam_resources(iam_client, role_name, instance_profile_name):
    try:
        if check_role_exists(iam_client, role_name):
            if instance_profile_name:
                try:
                    iam_client.remove_role_from_instance_profile(
                        InstanceProfileName=instance_profile_name,
                        RoleName=role_name
                    )
                    iam_client.delete_instance_profile(InstanceProfileName=instance_profile_name)
                    print(f"Deleted Instance Profile: {instance_profile_name}")
                except iam_client.exceptions.NoSuchEntityException:
                    print(f"Instance Profile '{instance_profile_name}' not found.")

            # 先解除與角色相關聯的策略
            detach_policies(iam_client, role_name)

            # 再刪除角色
            iam_client.delete_role(RoleName=role_name)
            print(f"Deleted IAM Role: {role_name}")
        else:
            print(f"IAM Role '{role_name}' not found.")
    except Exception as e:
        print(f"Error deleting IAM resources: {e}")

def delete_resources():
    try:
        # 初始化 boto3 客戶端
        session = boto3.Session(profile_name='harry-redteam')
        iam_client = session.client('iam')
        ec2_client = session.client('ec2', region_name='us-east-2')

        role_name = 'EC2TestRole'
        instance_profile_name = 'EC2TestProfile'
        key_name = 'my-key-pair'

        terminate_ec2_instances(ec2_client)
        delete_key_pair(ec2_client, key_name)
        delete_iam_resources(iam_client, role_name, instance_profile_name)
    except Exception as e:
        print(f"Error: {e}")

# 呼叫函數來刪除資源
delete_resources()
