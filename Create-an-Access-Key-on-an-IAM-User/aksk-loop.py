import boto3
import time

def create_account_and_keys(parent_access_key_id, parent_secret_access_key):
    client = boto3.client(
        'iam',
        aws_access_key_id=parent_access_key_id,
        aws_secret_access_key=parent_secret_access_key
    )

    # 創建用戶
    user_name = f"nested_user_{int(time.time())}"
    client.create_user(UserName=user_name)

    # 創建存取金鑰和安全金鑰
    response = client.create_access_key(UserName=user_name)
    access_key_id = response['AccessKey']['AccessKeyId']
    secret_access_key = response['AccessKey']['SecretAccessKey']

    # 為用戶附加"AdministratorAccess"策略
    client.attach_user_policy(
        UserName=user_name,
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
    )

    return user_name, access_key_id, secret_access_key

def test_access_key(access_key_id, secret_access_key):
    client = boto3.client(
        'iam',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    )
    try:
        # 嘗試獲取IAM用戶列表，以測試AK/SK是否有效
        client.list_users()
        return True
    except:
        return False

def wait_for_key_activation(access_key_id, secret_access_key, max_attempts=6, delay=10):
    for _ in range(max_attempts):
        if test_access_key(access_key_id, secret_access_key):
            return True
        time.sleep(delay)  # 等待一段時間後重試
    return False

def delete_keys(user_names, access_key_ids):
    client = boto3.client('iam')

    for user_name, access_key_id in zip(user_names, access_key_ids):
        # 移除指定的AK/SK
        client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)
        # 刪除用戶
        client.delete_user(UserName=user_name)

def main():
    initial_access_key_id = 'AxxxxxxxxxxxxxxNFIDM6'
    initial_secret_access_key = 'yWM2xxxxxxxxxxxxxxxxxxxxKnLx4yqf'

    current_ak = initial_access_key_id
    current_sk = initial_secret_access_key

    user_names = []
    access_key_ids = []

    for i in range(10):
        print(f"Creating user {i+1}")
        user_name, new_ak, new_sk = create_account_and_keys(current_ak, current_sk)
        user_names.append(user_name)
        access_key_ids.append(new_ak)
        print(f"Waiting for new keys to activate for user {user_name}")
        if wait_for_key_activation(new_ak, new_sk):
            print(f"Keys activated for user {user_name}")
            current_ak = new_ak
            current_sk = new_sk
        else:
            print(f"Failed to activate keys for user {user_name}, stopping process")
            break

    # 儲存或記錄用戶名和AK
    with open("aws_credentials.txt", "w") as file:
        for user_name, access_key_id in zip(user_names, access_key_ids):
            file.write(f"{user_name},{access_key_id}\n")

    # 之後可以透過以下函數移除這些AK/SK
    # delete_keys(user_names, access_key_ids)

if __name__ == "__main__":
    main()
