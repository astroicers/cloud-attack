import os
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

def delete_created_files():
    regions = get_all_regions()
    for region in regions:
        for filename in os.listdir('.'):
            if filename.startswith(region) and filename.endswith('.json'):
                os.remove(filename)
                print(f"Deleted file: {filename}")

# 主執行程序
def main():
    session = boto3.Session(profile_name='harry-redteam')
    # 調用刪除函數
    delete_created_files()
    print("所有由於專案建立的檔案已被刪除。")

main()
