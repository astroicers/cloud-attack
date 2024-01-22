import boto3
import json
import zipfile
import io
import time
import stat

# 初始化用來儲存生成資源的字典
generated_resources = {
    "roles": [],
    "lambda_functions": [],
    "iam_users": []
}

def create_lambda_role(role_name,access_key_id, secret_access_key):
    iam_client = boto3.client(
        'iam',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
        )

    # Lambda 服務的信任關係政策
    trust_relationship = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # 創建 IAM 角色
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_relationship),
            Description="Role for Lambda execution"
        )
        role_arn = role['Role']['Arn']
        print(f"Created role: {role_arn}")

        # 附加 AdministratorAccess 策略
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
        )
        print(f"Attached AdministratorAccess policy to role {role_name}")
        generated_resources["roles"].append({"role_name": role_name, "role_arn": role_arn})

        return role_arn

    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Role {role_name} already exists.")
        return None

def deploy_lambda_function(function_name,access_key_id, secret_access_key,account_id,region_name):
    lambda_client = boto3.client(
        'lambda',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name)

    # 打包Lambda函數代碼
    lambda_code = """
import boto3
import time
import json

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

def lambda_handler(event, context): 
    initial_access_key_id = event.get('access_key_id', 'default_ak')
    initial_secret_access_key = event.get('secret_access_key', 'default_sk')

    current_ak = initial_access_key_id
    current_sk = initial_secret_access_key

    user_name, new_ak, new_sk = create_account_and_keys(current_ak, current_sk)
    if wait_for_key_activation(new_ak, new_sk):
        current_ak = new_ak
        current_sk = new_sk
    else:
        raise Exception("New key is not activated")

    result_dict = {
    'user_name': user_name,
    'access_key_id': current_ak,
    'secret_access_key': current_sk
    }

    return {
        'statusCode': 200,
        'body': result_dict
    }
    """
    zip_output = io.BytesIO()
    with zipfile.ZipFile(zip_output, 'w') as zf:
        zip_info = zipfile.ZipInfo('lambda_function.py')
        zip_info.external_attr = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |  # 擁有者讀寫執行 (rwx)
                          stat.S_IRGRP | stat.S_IXGRP |               # 群組讀取執行 (rx)
                          stat.S_IROTH | stat.S_IXOTH) << 16          # 其他用戶讀取執行 (rx)

        zf.writestr('lambda_function.py', lambda_code)
    zip_output.seek(0)

    timeout_seconds = 60  # 設置超時時間，這裡設為 60 秒

    # 創建Lambda函數
    print("waiting for 10 seconds")
    time.sleep(10)
    response = lambda_client.create_function(
        FunctionName=function_name,
        Runtime='python3.8',
        Role='arn:aws:iam::%s:role/MyLambdaExecutionRole' % account_id,  # 替換為你的Lambda角色ARN
        Handler='lambda_function.lambda_handler',
        Timeout=timeout_seconds,
        Code={
            'ZipFile': zip_output.read()
        }
        # 其他配置...
    )

    # 更新生成資源字典
    generated_resources["lambda_functions"].append({"function_name": function_name, "function_arn": response['FunctionArn']})

    while True:
        response = lambda_client.get_function(FunctionName=function_name)
        if response['Configuration']['State'] == 'Active':
            print("Lambda function is now active.")
            break
        print("Waiting for Lambda function to become active...")
        time.sleep(10)  # 每10秒檢查一次

        

def invoke_lambda_function(function_name,access_key_id, secret_access_key,region_name):
    lambda_client = boto3.client(
    'lambda',
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
    region_name=region_name)
    # 觸發Lambda函數
    lambda_parameters = {
    'access_key_id': access_key_id,
    'secret_access_key': secret_access_key
    }
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(lambda_parameters))
    
    response_payload = json.loads(response['Payload'].read())
    # print("response:" + json.dumps(response_payload))
    result = json.dumps(response_payload)
    print("result:" + result)
    return result

def save_generated_resources():
    with open('generated_resources.json', 'w') as file:
        json.dump(generated_resources, file, indent=4)

def main():
    account_id = '350667048426'
    region_name = 'ap-southeast-1'
    session = boto3.Session(profile_name='peace-key',region_name=region_name)
    access_key_id=session.get_credentials().access_key
    secret_access_key=session.get_credentials().secret_key

    role_name = "MyLambdaExecutionRole"
    create_lambda_role(role_name,access_key_id, secret_access_key)

    # 觸發Lambda函數
    
    for i in range(16):
        # 部署並運行Lambda函數
        function_name = f"MyLambdaFunctionLoop{i+1}"  # 替換為您的 Lambda 函數名稱
        deploy_lambda_function(function_name,access_key_id, secret_access_key,account_id,region_name)
        print("Lambda Function Deployed and Executed")

        print(f"Invoking Lambda function {i+1}")
        result = invoke_lambda_function(function_name,access_key_id, secret_access_key,region_name)
        print(result)
        data = json.loads(result)
        body = data['body']
        user_name = body['user_name']
        access_key_id = body['access_key_id']
        secret_access_key = body['secret_access_key']
        # 更新生成資源字典
        if user_name and access_key_id and secret_access_key:
            generated_resources["iam_users"].append({
                "user_name": user_name,
                "access_key_id": access_key_id,
                "secret_access_key": secret_access_key
        })
    
    save_generated_resources()


if __name__ == "__main__":
    main()