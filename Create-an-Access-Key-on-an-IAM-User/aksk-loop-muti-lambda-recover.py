import boto3
import json

def delete_generated_resources(region_name):
    # 讀取 generated_resources.json 檔案
    with open('generated_resources.json', 'r') as file:
        resources = json.load(file)

    # 初始化 AWS 客戶端
    session = boto3.Session(profile_name='peace-key')
    iam_client = session.client('iam')
    lambda_client = session.client('lambda',region_name=region_name)

    # 刪除 IAM 用戶
    for user in resources.get("iam_users", []):
        user_name = user['user_name']
        try:
            # 列出用戶的所有附加政策
            attached_policies = iam_client.list_attached_user_policies(UserName=user_name)
            for policy in attached_policies.get('AttachedPolicies', []):
                # 解除附加的政策
                iam_client.detach_user_policy(
                    UserName=user_name,
                    PolicyArn=policy['PolicyArn']
                )

            # 刪除用戶的所有存取金鑰
            access_keys = iam_client.list_access_keys(UserName=user_name)
            for key in access_keys.get('AccessKeyMetadata', []):
                iam_client.delete_access_key(UserName=user_name, AccessKeyId=key['AccessKeyId'])

            # 最後刪除用戶
            iam_client.delete_user(UserName=user_name)
            print(f"Deleted IAM user: {user_name}")
        except Exception as e:
            print(f"Error deleting IAM user {user_name}: {e}")
        

    # 刪除 Lambda 函數
    for lambda_function in resources.get("lambda_functions", []):
        function_name = lambda_function['function_name']
        try:
            lambda_client.delete_function(FunctionName=function_name)
            print(f"Deleted Lambda function: {function_name}")
        except Exception as e:
            print(f"Error deleting Lambda function {function_name}: {e}")

    # 刪除 IAM 角色
    for role in resources.get("roles", []):
        role_name = role['role_name']
        try:
            # 首先解除角色的策略綁定
            policies = iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in policies['AttachedPolicies']:
                iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])

            iam_client.delete_role(RoleName=role_name)
            print(f"Deleted IAM role:{role_name}")
        except Exception as e:
            print(f"Error deleting IAM role {role_name}: {e}")

if __name__ == "__main__":
    # 執行刪除資源的函數
    region_name = 'ap-southeast-1'
    delete_generated_resources(region_name)
