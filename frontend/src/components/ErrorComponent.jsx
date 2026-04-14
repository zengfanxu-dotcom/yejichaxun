import React from 'react';
import { Alert, Typography } from 'antd';

const { Text } = Typography;

const ErrorComponent = ({ error, onRetry }) => {
  if (!error) return null;

  return (
    <div className="error-wrap">
      <Alert
        message="分析失败"
        description={
          <div>
            <Text type="danger">{error}</Text>
            {onRetry && (
              <button
                onClick={onRetry}
                className="primary-btn retry-btn"
              >
                重新上传
              </button>
            )}
          </div>
        }
        type="error"
        showIcon
        className="error-alert"
      />
    </div>
  );
};

export default ErrorComponent;