import boto3

# 獲取所有 AWS 區域
def get_all_regions():
    regions = [
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        # "af-south-1",
        "ap-east-1",
        "ap-south-1",
        "ap-northeast-3",
        "ap-northeast-2",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ca-central-1",
        # "cn-north-1",
        # "cn-northwest-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        # "eu-south-1",
        "eu-west-3",
        "eu-north-1",
        # "me-south-1",
        "sa-east-1"
    ]

    return regions

# 獲取指定區域中所有秘密的名稱
def get_all_secret_names(secretsmanager_client):
    secret_names = []
    try:
        paginator = secretsmanager_client.get_paginator('list_secrets')
        for page in paginator.paginate():
            for secret in page['SecretList']:
                secret_names.append(secret['Name'])
    except Exception as e:
        print(f"Error retrieving secret names: {str(e)}")
    return secret_names

# 檢索並保存秘密
def retrieve_and_save_secrets(secretsmanager_client, region, secret_names):
    for name in secret_names:
        try:
            secret = secretsmanager_client.get_secret_value(SecretId=name)
            secret_value = secret['SecretString']

            # 替換秘密名稱中的特殊字符
            safe_name = name.replace('/', '_')

            # 保存秘密到檔案
            with open(f"{region}_{safe_name}.json", "w") as file:
                file.write(secret_value)
        except Exception as e:
            print(f"Error retrieving secret {name} in region {region}: {str(e)}")

# 主執行程序
def main():
    session = boto3.Session(profile_name='peace-key')
    regions = get_all_regions()
    print(f"Processing regions: {regions}")
    
    for region in regions:
        print(f"Processing region: {region}")
        secretsmanager_client = session.client('secretsmanager', region_name=region)
        secret_names = get_all_secret_names(secretsmanager_client)
        retrieve_and_save_secrets(secretsmanager_client, region, secret_names)
    
    print("所有區域的秘密已被檢索並保存為檔案。")

if __name__ == "__main__":
    main()
