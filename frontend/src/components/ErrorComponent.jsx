import React from 'react';
import { Alert, Typography } from 'antd';

const { Text } = Typography;

const ErrorComponent = ({ error, onRetry }) => {
  if (!error) return null;

  return (
    <div style={styles.container}>
      <Alert
        message="分析失败"
        description={
          <div>
            <Text type="danger">{error}</Text>
            {onRetry && (
              <button 
                onClick={onRetry}
                style={styles.retryButton}
              >
                重新上传
              </button>
            )}
          </div>
        }
        type="error"
        showIcon
        style={styles.alert}
      />
    </div>
  );
};

const styles = {
  container: {
    marginTop: '20px',
    maxWidth: '600px',
  },
  alert: {
    borderRadius: '10px',
  },
  retryButton: {
    marginTop: '10px',
    padding: '6px 12px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

export default ErrorComponent;