// API测试脚本
// 在浏览器控制台中运行此脚本来测试API连接

(async function testAPI() {
  console.log('🧪 开始测试API连接...');
  
  try {
    // 测试健康检查
    console.log('1. 测试健康检查...');
    const healthResponse = await fetch('http://localhost:8000/health');
    const healthData = await healthResponse.json();
    console.log('✅ 健康检查:', healthData);
    
    // 测试股票数据
    console.log('2. 测试股票数据...');
    const stocksResponse = await fetch('http://localhost:8000/api/stocks');
    const stocksData = await stocksResponse.json();
    console.log('✅ 股票数据:', stocksData);
    
    // 测试AI聊天
    console.log('3. 测试AI聊天...');
    const chatResponse = await fetch('http://localhost:8000/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: '你好'
      })
    });
    const chatData = await chatResponse.json();
    console.log('✅ AI聊天:', chatData);
    
    console.log('🎉 所有API测试通过！');
    
  } catch (error) {
    console.error('❌ API测试失败:', error);
  }
})();
