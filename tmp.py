# main.pyの先頭付近でこのようなコードを追加
import os
from dotenv import load_dotenv

# .envファイルをロード
load_dotenv()

# 環境変数の値を表示
print(f"PRICE_UPDATE_INTERVAL={os.getenv('PRICE_UPDATE_INTERVAL')}")