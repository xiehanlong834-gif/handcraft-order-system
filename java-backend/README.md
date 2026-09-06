# java-backend —— 业务接口层（Java REST API）

> ⚠️ **状态：脚手架（未在本机编译验证）**。本仓库开发机无 JDK/Maven，代码按 Spring Boot 3 + JDK 17 规范编写，需在有对应环境的机器上 `mvn compile` 验证后继续开发。

## 职责（对应规划文档"业务接口层"）

- 统一账号权限校验（RBAC，四类角色越权拦截）
- 订单状态流转控制（状态机见 `OrderStatus`）
- 基础数据增删改查、非法数据拦截
- 调用本地 Python 脚本：智能订单分类（`OrderClassifierClient`）、数据分析（analytics.py）

## 已包含

| 文件 | 说明 |
|---|---|
| `pom.xml` | Spring Boot 3.2.5 / Java 17 / web + jdbc + mysql + security |
| `OrderApplication.java` | 启动类 |
| `order/OrderStatus.java` | 订单状态机（待确认→制作中→待发货→已完成，含取消/归档），非法流转在此拦截 |
| `order/OrderType.java` | 订单类型枚举（与 schema.sql / Python 端一致） |
| `classifier/OrderClassifierClient.java` | ProcessBuilder 调 python/order_classifier.py，解析最后一行 JSON |
| `resources/application.yml` | 数据源/脚本路径/端口配置模板 |

## 待开发（按 P0 → P1 顺序）

1. Security 配置：登录鉴权、BCrypt、按角色放行接口
2. 订单 Controller/Service/Mapper：建单（调分类器→写库→更新排期）、状态流转、列表/详情
3. 库存模块：出入库登记（触发 stock_movement 由 DB 触发器维护库存）
4. 成本利润：材料成本+工时成本录入、利润查询（视图 v_order_profit）
5. 客户/用户/基础数据 CRUD（管理员）
6. 报表接口：定时/按需调用 analytics.py 产出经营报表

## REST API 规划（草案，接口文档先行）

| 方法 | 路径 | 角色 | 说明 |
|---|---|---|---|
| POST | /api/auth/login | 公开 | 登录拿 token |
| POST | /api/orders | 创作者/客户 | 建单（客户仅本人+source=CUSTOMER） |
| GET | /api/orders?status= | 创作者/客户(本人) | 订单列表按状态筛选 |
| PATCH | /api/orders/{id}/status | 创作者 | 状态流转（状态机校验） |
| POST | /api/orders/{id}/cost | 创作者 | 录入材料/工时成本 |
| GET/POST | /api/materials | 创作者 | 库存列表/入库 |
| POST | /api/materials/{id}/out | 创作者 | 出库(关联订单) |
| GET | /api/materials/low-stock | 创作者 | 低库存预警(v_low_stock) |
| GET | /api/orders/due-reminder | 创作者 | 3 天工期提醒(v_due_reminder) |
| GET | /api/customers | 创作者 | 客户管理 |
| GET | /api/reports/profit-trend | 管理员/财务 | 利润趋势(调 analytics.py) |
| GET | /api/reports/repurchase | 管理员/财务 | 客户复购 |
| GET | /api/reports/materials | 管理员/财务 | 材料消耗 |
| CRUD | /api/users, /api/categories | 管理员 | 用户管理、基础数据 |

## 运行（在装有 JDK17+Maven 的机器上）

```bash
cd java-backend
mvn compile          # 先验证编译
mvn spring-boot:run  # 或 mvn package 后 java -jar target/order-backend-*.jar
```