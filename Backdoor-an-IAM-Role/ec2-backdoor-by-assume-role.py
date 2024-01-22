import os
import time
import boto3
import json

def create_iam_role(iam_client):
  trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }

  try:
    role = iam_client.get_role(RoleName='EC2TestRole')
    print("Role already exists.")
  except iam_client.exceptions.NoSuchEntityException:
    role = iam_client.create_role(
      RoleName='EC2TestRole',
      AssumeRolePolicyDocument=json.dumps(trust_policy)
    )
    print("Role created.")

  # Attach the 'AdministratorAccess' managed policy
  iam_client.attach_role_policy(
    RoleName='EC2TestRole',
    PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
  )
  print("AdministratorAccess policy attached to the role.")

def create_instance_profile(iam_client):
  try:
    instance_profile_info = iam_client.get_instance_profile(InstanceProfileName='EC2TestProfile')
    print("Instance profile already exists.")
    
    # 檢查 Instance Profile 是否已綁定角色
    if not instance_profile_info['InstanceProfile']['Roles']:
      print("Binding Role to Instance Profile...")
      iam_client.add_role_to_instance_profile(
        InstanceProfileName='EC2TestProfile',
        RoleName='EC2TestRole'
      )
      print("Role successfully bound to Instance Profile.")
    else:
      print("Instance Profile is already bound to a Role.")
  except iam_client.exceptions.NoSuchEntityException:
    iam_client.create_instance_profile(InstanceProfileName='EC2TestProfile')
    iam_client.add_role_to_instance_profile(
      InstanceProfileName='EC2TestProfile',
      RoleName='EC2TestRole'
    )

def create_key_pair(ec2_client):
  key_pair_name = 'my-key-pair'
  try:
    ec2_client.describe_key_pairs(KeyNames=[key_pair_name])
    print("Key Pair already exists.")
  except ec2_client.exceptions.ClientError:
    new_key_pair = ec2_client.create_key_pair(KeyName=key_pair_name)
    private_key = new_key_pair['KeyMaterial']
    filename = f"{key_pair_name}.pem"
    with open(filename, 'w') as file:
      file.write(private_key)
    os.chmod(filename, 0o400)

def create_ec2_instance(ec2_client, ami_id, instance_type):
  time.sleep(10)
  try:
    ec2_response = ec2_client.run_instances(
      ImageId=ami_id,
      MinCount=1,
      MaxCount=1,
      InstanceType=instance_type,
      KeyName='my-key-pair',
      IamInstanceProfile={
        'Name': 'EC2TestProfile'
      }
    )
    instance_id = ec2_response['Instances'][0]['InstanceId']
    print("EC2 Instance Created:", instance_id)

    # Add tags to the created instance
    ec2_client.create_tags(
      Resources=[instance_id],
      Tags=[
        {'Key': 'Name', 'Value': 'MyInstance'},
        {'Key': 'Environment', 'Value': 'Production'}
      ]
    )
  except ec2_client.exceptions.ClientError as e:
    print(f"Error creating EC2 instance: {e}")

if __name__ == "__main__":
  session = boto3.Session(profile_name='harry-redteam')
  iam_client = session.client('iam')
  ec2_client = session.client('ec2', region_name='us-east-2')

  create_iam_role(iam_client)
  create_instance_profile(iam_client)
  create_key_pair(ec2_client)
  ami_id = 'ami-0cd3c7f72edd5b06d'
  instance_type = 't2.micro'
  create_ec2_instance(ec2_client,ami_id,instance_type)
