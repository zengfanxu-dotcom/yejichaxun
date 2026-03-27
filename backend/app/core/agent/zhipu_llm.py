import os
import logging
from zhipuai import ZhipuAI

# 配置日志
logger = logging.getLogger(__name__)

class ZhipuLLM:
    def __init__(self):
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            logger.error("ZHIPU_API_KEY 环境变量未设置")
            raise EnvironmentError("ZHIPU_API_KEY 环境变量未设置")
        
        logger.info("初始化ZhipuAI客户端")
        self.client = ZhipuAI(api_key=api_key)

    def invoke(self, prompt: str) -> str:
        logger.info(f"调用ZhipuAI模型: glm-4-flash")
        logger.info(f"发送提示词，长度: {len(prompt)} 字符")
        
        try:
            response = self.client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1024
            )
            
            # 使用最简单的方式访问响应
            try:
                result = response.choices[0].message.content
                if result is not None:
                    logger.info(f"API调用成功，返回结果长度: {len(result)} 字符")
                    return result
                else:
                    logger.error("响应内容为None")
                    return "API响应内容为空"
            except Exception as e:
                logger.error(f"响应结构访问错误: {str(e)}")
                return "API响应结构异常"
            
        except Exception as e:
            logger.error(f"ZhipuAI API调用失败: {str(e)}", exc_info=True)
            return f"ZhipuAI API调用失败: {str(e)}"