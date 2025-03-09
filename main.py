# main.py
import asyncio
import logging
import os
from dotenv import load_dotenv

from src.config import AppConfig
from src.price_monitoring import PriceMonitor
from src.arbitrage_detection import ArbitrageDetector
from src.data_management import DataManager
from src.notification import SlackNotifier

# ロギングの設定
def setup_logging():
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"{log_dir}/app.log"),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("dex_arbitrage_bot")

async def main():
    # 環境変数の読み込み
    load_dotenv()
    
    # ロギングのセットアップ
    logger = setup_logging()
    logger.info("DEXアービトラージボットを起動しています...")
    
    # 設定の読み込み
    config = AppConfig()
    logger.info(f"設定を読み込みました: 価格更新間隔={config.price_update_interval}秒, 裁定閾値={config.arbitrage_threshold}%")
    
    # 各モジュールの初期化
    data_manager = DataManager(config)
    await data_manager.initialize()
    
    slack_notifier = SlackNotifier(config.slack_webhook_url)
    
    price_monitor = PriceMonitor(config, data_manager)
    arbitrage_detector = ArbitrageDetector(config, data_manager, slack_notifier)
    
    # 価格モニタリングの開始
    price_monitor_task = asyncio.create_task(price_monitor.start_monitoring())
    
    # 裁定検出の開始
    arbitrage_detector_task = asyncio.create_task(arbitrage_detector.start_detection())
    
    try:
        # 両方のタスクが完了するまで待機
        await asyncio.gather(price_monitor_task, arbitrage_detector_task)
    except KeyboardInterrupt:
        logger.info("プログラムを終了します...")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
    finally:
        # リソースのクリーンアップ
        await data_manager.cleanup()
        logger.info("プログラムを終了しました")

if __name__ == "__main__":
    asyncio.run(main())