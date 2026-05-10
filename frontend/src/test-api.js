// 简单的API测试脚本
fetch('/api/stocks')
  .then(response => response.json())
  .then(data => {
    console.log('API响应:', data);
    console.log('股票数量:', data.data?.stocks?.length);
    console.log('股票示例:', data.data?.stocks?.[0]);
  })
  .catch(error => {
    console.error('API错误:', error);
  });
