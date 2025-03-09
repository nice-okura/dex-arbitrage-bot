# src/notification.py
import logging
import aiohttp
from typing import Dict, Any

logger = logging.getLogger("dex_arbitrage_bot.notification")

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
        # webhook_urlが設定されていない場合は警告を出す
        if not webhook_url:
            logger.warning("Slack webhook URLが設定されていません。Slack通知は無効です。")
    
    async def send_notification(self, message: str):
        """Slackに通知を送信する"""
        if not self.webhook_url:
            logger.info(f"Slack通知（無効）: {message}")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": message,
                    "mrkdwn": True
                }
                
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"Slack通知の送信に失敗しました: {response.status} - {response_text}")
                    else:
                        logger.info("Slack通知を送信しました")
        
        except Exception as e:
            logger.error(f"Slack通知の送信中にエラーが発生しました: {e}", exc_info=True)