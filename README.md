Fetch Cache 测试清单
同步测试 (HTTPClient)
✅ Redis 缓存测试
[x] 基本 GET 请求测试
[x] 缓存命中验证
[x] Redis 值校验
[x] 过期时间验证
✅ Memory 缓存测试
[x] 基本 GET 请求测试
[x] 缓存命中验证
[x] 内存值校验
[x] 过期时间验证
⬜ MongoDB 缓存测试
[ ] 基本 GET 请求测试
[ ] 缓存命中验证
[ ] MongoDB 文档校验
[ ] 过期时间验证
⬜ SQL 缓存测试
[ ] MySQL 缓存测试
[ ] PostgreSQL 缓存测试
[ ] SQLite 缓存测试
[ ] MariaDB 缓存测试
⬜ Django 缓存测试
[ ] Django Cache 后端测试
[ ] Django DB 后端测试
[ ] Django Settings 配置测试
异步测试 (AsyncHTTPClient)
✅ File 缓存测试
[x] 基本 GET 请求测试
[x] 缓存命中验证
[x] 文件内容校验
[x] 过期时间验证
⬜ Redis 缓存测试
[ ] 基本 GET 请求测试
[ ] 缓存命中验证
[ ] Redis 值校验
[ ] 过期时间验证
✅Memory 缓存测试
[x] 基本 GET 请求测试
[x] 缓存命中验证
[x] 内存值校验
[x] 过期时间验证
⬜ MongoDB 缓存测试
[ ] 基本 GET 请求测试
[ ] 缓存命中验证
[ ] MongoDB 文档校验
[ ] 过期时间验证
⬜ SQL 缓存测试
[ ] MySQL 缓存测试
[ ] PostgreSQL 缓存测试
[ ] SQLite 缓存测试
[ ] MariaDB 缓存测试
⬜ Django 缓存测试
[ ] Django Cache 后端测试
[ ] Django DB 后端测试
[ ] Django Settings 配置测试
通用测试项
⬜ 错误处理测试
[ ] 连接失败处理
[ ] 超时处理
[ ] 无效配置处理
[ ] 并发访问处理
⬜ 性能测试
[ ] 缓存读写性能
[ ] 并发性能
[ ] 内存占用
[ ] 响应时间
⬜ 清理测试
[ ] 过期缓存自动清理
[ ] 手动清理功能
[ ] 资源释放验证