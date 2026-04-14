import os
import logging
import httpx
from zhipuai import ZhipuAI

# 配置日志
logger = logging.getLogger(__name__)

class ZhipuLLM:
    def __init__(self):
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            logger.error("ZHIPU_API_KEY 环境变量未设置")
            raise EnvironmentError("ZHIPU_API_KEY 环境变量未设置")

        trust_env = os.getenv("ZHIPU_TRUST_ENV", "0") == "1"
        timeout = float(os.getenv("ZHIPU_TIMEOUT_SECONDS", "30"))

        # 默认禁用对系统代理/环境代理的继承，避免代理链路 TLS 异常影响直连。
        http_client = httpx.Client(trust_env=trust_env, timeout=timeout)
        logger.info("初始化ZhipuAI客户端")
        self.client = ZhipuAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=2,
            http_client=http_client,
        )

    def invoke(self, prompt: str) -> str:
        logger.info(f"调用ZhipuAI模型: glm-4-flash")
        logger.info(f"发送提示词，长度: {len(prompt)} 字符")

        try:
            response = self.client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024
            )

            # 使用最简单的方式访问响应
            result = response.choices[0].message.content
            if result is None:
                raise RuntimeError("智谱返回内容为空")
            logger.info(f"API调用成功，返回结果长度: {len(result)} 字符")
            return result

        except Exception as e:
            logger.error(f"ZhipuAI API调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"ZhipuAI API调用失败: {str(e)}") from e