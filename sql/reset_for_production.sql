-- =============================================================
-- 生产化重置脚本: 清空全部演示/测试数据, 保留系统结构
-- 适用: 从"课程演示状态"切换到"真实使用状态"
-- 执行: mysql -u root -p --default-character-set=utf8mb4 < reset_for_production.sql
-- 说明: 角色表(4类)与库结构保留; 订单/客户/库存/公告/账号全部清空重建
-- =============================================================
USE handcraft_order;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE order_material;
TRUNCATE TABLE order_status_log;
TRUNCATE TABLE stock_movement;
TRUNCATE TABLE announcement;
TRUNCATE TABLE `orders`;
TRUNCATE TABLE customer;
TRUNCATE TABLE material;
TRUNCATE TABLE product_category;
TRUNCATE TABLE material_category;
-- 清空全部账号(含演示账号 creator01/admin01/finance01/xiaolin/may)
TRUNCATE TABLE `user`;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------- 重建最小必要账号(密码占位, 请改为你的密码后执行) ----------
-- 密码生成方法: python -c "import bcrypt;print(bcrypt.hashpw(b'你的密码',bcrypt.gensalt(rounds=10,prefix=b'2a')).decode())"
-- 示例: admin 密码 Admin@2026 / 店主密码 Creator@2026 (自行替换 $2a$10$szhrrnM1CEZzj4aInOhc7efYkoblIMV9MwVlazxn/6V96shWFUgdq/$2a$10$szhrrnM1CEZzj4aInOhc7efYkoblIMV9MwVlazxn/6V96shWFUgdq)

INSERT INTO `user` (username, password_hash, real_name, role_id, status)
SELECT 'admin', '$2a$10$szhrrnM1CEZzj4aInOhc7efYkoblIMV9MwVlazxn/6V96shWFUgdq', '系统管理员', role_id, 1 FROM role WHERE role_code = 'admin';

INSERT INTO `user` (username, password_hash, real_name, role_id, status)
SELECT 'creator', '$2a$10$szhrrnM1CEZzj4aInOhc7efYkoblIMV9MwVlazxn/6V96shWFUgdq', '店主(请改真实姓名)', role_id, 1 FROM role WHERE role_code = 'creator';

-- 需要财务账号? 登录 admin 后在"管理后台-新建用户"里创建, 角色选 finance 即可