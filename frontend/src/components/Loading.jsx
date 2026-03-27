import React from 'react';
import { Spin, Typography } from 'antd';

const { Text } = Typography;

const LoadingComponent = ({ message = "分析中，请稍候..." }) => {
  return (
    <div className="loading-container">
      <Spin size="large" />
      <Text type="secondary" className="loading-text">
        {message}
      </Text>
    </div>
  );
};

export default LoadingComponent;