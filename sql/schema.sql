-- =============================================================
-- 独立手作创作者订单管理系统 - MySQL 8.0 建库脚本
-- 设计原则：数据库三范式；InnoDB；utf8mb4；外键 RESTRICT
-- 执行方式: mysql -u root -p < sql/schema.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS handcraft_order
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE handcraft_order;

-- -------------------------------------------------------------
-- 1. 角色表（四类角色：creator 创作者 / customer 客户 /
--                 admin 管理员 / finance 财务查看者）
-- -------------------------------------------------------------
CREATE TABLE role (
  role_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_code   VARCHAR(20)  NOT NULL UNIQUE COMMENT '角色编码',
  role_name   VARCHAR(50)  NOT NULL COMMENT '角色名称',
  description VARCHAR(200) NULL COMMENT '角色说明'
) ENGINE=InnoDB COMMENT='系统角色';

-- -------------------------------------------------------------
-- 2. 用户表（登录账号；密码 BCrypt 加密存储；管理员/创作者/财务查看者）
--    客户如注册账号也入本表 role_code=customer
-- -------------------------------------------------------------
CREATE TABLE `user` (
  user_id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE COMMENT '登录名',
  password_hash VARCHAR(100) NOT NULL COMMENT 'BCrypt 密码哈希',
  real_name     VARCHAR(50)  NULL COMMENT '姓名',
  phone         VARCHAR(20)  NULL COMMENT '手机号(界面脱敏展示)',
  role_id       INT UNSIGNED NOT NULL COMMENT '角色',
  status        TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_role FOREIGN KEY (role_id) REFERENCES role (role_id)
) ENGINE=InnoDB COMMENT='系统用户';

-- -------------------------------------------------------------
-- 3. 客户表（创作者维护；敏感字段脱敏展示）
-- -------------------------------------------------------------
CREATE TABLE customer (
  customer_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(50)  NOT NULL COMMENT '客户称呼',
  phone       VARCHAR(20)  NULL COMMENT '手机号(界面脱敏)',
  wechat_id   VARCHAR(50)  NULL COMMENT '微信号',
  tags        VARCHAR(200) NULL COMMENT '客户标签(画像用,逗号分隔)',
  creator_id  INT UNSIGNED NOT NULL COMMENT '归属创作者(user_id)',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_customer_creator FOREIGN KEY (creator_id) REFERENCES `user` (user_id)
) ENGINE=InnoDB COMMENT='客户';

-- -------------------------------------------------------------
-- 4. 产品分类（基础数据，管理员维护）
-- -------------------------------------------------------------
CREATE TABLE product_category (
  product_category_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name                VARCHAR(50) NOT NULL UNIQUE COMMENT '如:手工饰品/皮具/烘焙/陶艺/编织',
  sort_no             INT         NOT NULL DEFAULT 0
) ENGINE=InnoDB COMMENT='产品分类';

-- -------------------------------------------------------------
-- 5. 材料品类（基础数据，管理员维护）
-- -------------------------------------------------------------
CREATE TABLE material_category (
  material_category_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name                 VARCHAR(50) NOT NULL UNIQUE COMMENT '如:金属/皮革/陶土/线材'
) ENGINE=InnoDB COMMENT='材料品类';

-- -------------------------------------------------------------
-- 6. 材料表（库存主档：当前库存量 + 低库存阈值）
-- -------------------------------------------------------------
CREATE TABLE material (
  material_id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  material_category_id INT UNSIGNED NOT NULL,
  name                 VARCHAR(100) NOT NULL COMMENT '材料名称',
  spec                 VARCHAR(100) NULL COMMENT '规格',
  unit                 VARCHAR(10)  NOT NULL DEFAULT '件' COMMENT '单位:件/克/米/个',
  stock_qty            DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '当前库存',
  low_stock_threshold  DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '低库存预警阈值',
  unit_price           DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '材料单价(成本核算用)',
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_material_cat FOREIGN KEY (material_category_id)
    REFERENCES material_category (material_category_id)
) ENGINE=InnoDB COMMENT='材料库存主档';

-- -------------------------------------------------------------
-- 7. 库存流水（入库/出库统一流水，触发器维护 material.stock_qty）
-- -------------------------------------------------------------
CREATE TABLE stock_movement (
  movement_id  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  material_id  INT UNSIGNED NOT NULL,
  direction    ENUM('IN','OUT') NOT NULL COMMENT 'IN入库 OUT出库(订单耗用)',
  quantity     DECIMAL(12,2) NOT NULL COMMENT '变动数量(>0)',
  order_id     INT UNSIGNED NULL COMMENT '出库关联订单(订单耗料)',
  operator_id  INT UNSIGNED NOT NULL COMMENT '操作人',
  note         VARCHAR(200) NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_move_material FOREIGN KEY (material_id) REFERENCES material (material_id),
  CONSTRAINT fk_move_operator FOREIGN KEY (operator_id) REFERENCES `user` (user_id)
) ENGINE=InnoDB COMMENT='库存出入库流水';

-- -------------------------------------------------------------
-- 8. 订单表（P0 核心）
--    订单类型: CUSTOM定制 / READY现货 / BATCH批量 / GENERAL通用(兜底)
--    状态机: PENDING_CONFIRM待确认→IN_PRODUCTION制作中→PENDING_SHIPMENT待发货
--           →COMPLETED已完成；CANCELLED取消；ARCHIVED归档
--    成本字段由创作者录入(材料成本合计+工时成本)，利润由视图/服务计算
-- -------------------------------------------------------------
CREATE TABLE `orders` (
  order_id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_no               VARCHAR(32)  NOT NULL UNIQUE COMMENT '订单号(生成规则见后端)',
  customer_id            INT UNSIGNED NOT NULL COMMENT '下单客户',
  creator_id             INT UNSIGNED NOT NULL COMMENT '负责创作者(user_id)',
  product_category_id    INT UNSIGNED NULL COMMENT '产品分类',
  product_name           VARCHAR(200) NOT NULL COMMENT '产品名称/描述',
  requirement            TEXT NULL COMMENT '定制要求(客户定制需求)',
  order_type             ENUM('CUSTOM','READY','BATCH','GENERAL') NOT NULL
                         COMMENT '智能分类结果:定制/现货/批量/通用',
  quantity               INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '数量',
  unit_price             DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '单价',
  material_cost          DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '材料成本合计(录入)',
  labor_cost             DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '工时成本(录入)',
  status                 ENUM('PENDING_CONFIRM','IN_PRODUCTION','PENDING_SHIPMENT',
                              'COMPLETED','CANCELLED','ARCHIVED') NOT NULL
                         DEFAULT 'PENDING_CONFIRM' COMMENT '订单状态',
  estimate_days          INT NULL COMMENT '预估工期(天,智能分类计算)',
  estimated_complete_date DATE NULL COMMENT '预估完成日期',
  actual_complete_date   DATE NULL COMMENT '实际完成日期',
  source                 ENUM('MANUAL','CUSTOMER') NOT NULL DEFAULT 'MANUAL'
                         COMMENT '订单来源:创作者手动/客户提交',
  remark                 VARCHAR(500) NULL,
  created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id),
  CONSTRAINT fk_order_creator  FOREIGN KEY (creator_id)  REFERENCES `user` (user_id),
  CONSTRAINT fk_order_pcat     FOREIGN KEY (product_category_id)
                         REFERENCES product_category (product_category_id),
  CONSTRAINT chk_qty CHECK (quantity >= 1)
) ENGINE=InnoDB COMMENT='订单(核心表)';

-- -------------------------------------------------------------
-- 9. 订单状态流转日志（审计：谁在何时把订单从什么状态改到什么状态）
-- -------------------------------------------------------------
CREATE TABLE order_status_log (
  log_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id    INT UNSIGNED NOT NULL,
  from_status VARCHAR(30) NULL,
  to_status   VARCHAR(30) NOT NULL,
  operator_id INT UNSIGNED NOT NULL COMMENT '操作人(仅创作者/管理员可流转)',
  note        VARCHAR(200) NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_log_order    FOREIGN KEY (order_id)    REFERENCES `orders` (order_id),
  CONSTRAINT fk_log_operator FOREIGN KEY (operator_id) REFERENCES `user` (user_id)
) ENGINE=InnoDB COMMENT='订单状态流转日志';

-- -------------------------------------------------------------
-- 10. 订单-材料耗用明细（订单完成→扣减库存→材料消耗分析的数据源）
-- -------------------------------------------------------------
CREATE TABLE order_material (
  order_material_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_id          INT UNSIGNED NOT NULL,
  material_id       INT UNSIGNED NOT NULL,
  quantity_used     DECIMAL(12,2) NOT NULL COMMENT '耗用数量',
  unit_cost         DECIMAL(10,2) NOT NULL COMMENT '耗用当时单价快照',
  CONSTRAINT fk_om_order    FOREIGN KEY (order_id)    REFERENCES `orders` (order_id),
  CONSTRAINT fk_om_material FOREIGN KEY (material_id) REFERENCES material (material_id)
) ENGINE=InnoDB COMMENT='订单材料耗用明细';

-- -------------------------------------------------------------
-- 11. 公告表（P2 简化版：管理员发布，全员查看）
-- -------------------------------------------------------------
CREATE TABLE announcement (
  announcement_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title           VARCHAR(200) NOT NULL,
  content         TEXT NULL,
  publisher_id    INT UNSIGNED NOT NULL COMMENT '管理员',
  status          TINYINT NOT NULL DEFAULT 1 COMMENT '1发布 0下线',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ann_user FOREIGN KEY (publisher_id) REFERENCES `user` (user_id)
) ENGINE=InnoDB COMMENT='公告';

-- -------------------------------------------------------------
-- 12. 触发器：库存流水入库自动累加 / 出库自动扣减 material.stock_qty
-- -------------------------------------------------------------
DELIMITER $$
CREATE TRIGGER trg_stock_movement_in AFTER INSERT ON stock_movement
FOR EACH ROW
BEGIN
  IF NEW.direction = 'IN' THEN
    UPDATE material SET stock_qty = stock_qty + NEW.quantity
      WHERE material_id = NEW.material_id;
  ELSE
    UPDATE material SET stock_qty = stock_qty - NEW.quantity
      WHERE material_id = NEW.material_id;
  END IF;
END$$
DELIMITER ;

-- -------------------------------------------------------------
-- 13. 视图：订单利润明细（收入 - 材料成本 - 工时成本）
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_order_profit AS
SELECT o.order_id, o.order_no, o.customer_id, c.name AS customer_name,
       o.order_type, o.status, o.quantity, o.unit_price,
       o.quantity * o.unit_price                      AS income,
       o.material_cost + o.labor_cost                 AS total_cost,
       o.quantity * o.unit_price - o.material_cost - o.labor_cost AS profit,
       o.created_at, o.actual_complete_date
FROM `orders` o
JOIN customer c ON c.customer_id = o.customer_id
WHERE o.status IN ('COMPLETED','ARCHIVED');

-- -------------------------------------------------------------
-- 14. 视图：低库存预警（stock_qty <= 阈值 且未禁用材料…按阈值判定）
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_low_stock AS
SELECT m.material_id, m.name, m.spec, m.unit, m.stock_qty,
       m.low_stock_threshold, m.unit_price
FROM material m
WHERE m.stock_qty <= m.low_stock_threshold;

-- -------------------------------------------------------------
-- 15. 视图：距预估完成日期 <= 3 天且未完成的订单 → 工期提醒
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_due_reminder AS
SELECT o.order_id, o.order_no, c.name AS customer_name, o.product_name,
       o.order_type, o.estimated_complete_date, o.status
FROM `orders` o
JOIN customer c ON c.customer_id = o.customer_id
WHERE o.status NOT IN ('COMPLETED','CANCELLED','ARCHIVED')
  AND o.estimated_complete_date IS NOT NULL
  AND DATEDIFF(o.estimated_complete_date, CURDATE()) BETWEEN 0 AND 3;

-- =============================================================
-- 初始化数据（演示用）
-- 说明: 生产环境请由后端注册接口写入 BCrypt 哈希，勿直接使用示例密码
-- =============================================================
INSERT INTO role (role_code, role_name, description) VALUES
('creator', '创作者',   '订单/库存/排期/客户 全流程管理'),
('customer','客户',     '提交定制需求、追踪订单进度'),
('admin',   '管理员',   '用户管理、基础数据配置、数据统计'),
('finance', '财务查看者','专职查看经营报表与成本明细(只读)');

INSERT INTO `user` (username, password_hash, real_name, role_id) VALUES
('creator01', '$2a$10$HASH_REPLACE_ME', '陈手作',  (SELECT role_id FROM role WHERE role_code='creator')),
('admin01',   '$2a$10$HASH_REPLACE_ME', '系统管理员', (SELECT role_id FROM role WHERE role_code='admin')),
('finance01', '$2a$10$HASH_REPLACE_ME', '账房先生', (SELECT role_id FROM role WHERE role_code='finance'));

INSERT INTO product_category (name, sort_no) VALUES
('手工饰品',1),('皮具',2),('烘焙',3),('陶艺',4),('编织',5);

INSERT INTO material_category (name) VALUES
('金属配件'),('皮革'),('烘焙原料'),('陶土'),('线材');

INSERT INTO material (material_category_id, name, spec, unit, stock_qty, low_stock_threshold, unit_price) VALUES
((SELECT material_category_id FROM material_category WHERE name='金属配件'), '925银链', '45cm', '条',  120, 20,  8.00),
((SELECT material_category_id FROM material_category WHERE name='金属配件'), '龙虾扣',  '通用',   '个',  800, 100, 0.50),
((SELECT material_category_id FROM material_category WHERE name='皮革'),    '植鞣革',  '1.5mm', '平方尺', 40, 10, 12.00),
((SELECT material_category_id FROM material_category WHERE name='烘焙原料'), '低筋面粉','1kg装', '袋',  25, 5,   6.50),
((SELECT material_category_id FROM material_category WHERE name='陶土'),    '白陶泥',  '5kg装', '袋',  15, 5,  28.00);

INSERT INTO customer (name, phone, wechat_id, tags, creator_id) VALUES
('小林', '13800001111', 'xiaolin_88', '老客,高复购,定制偏好', (SELECT user_id FROM `user` WHERE username='creator01')),
('阿May', '13800002222', 'may_may',   '新客,饰品',          (SELECT user_id FROM `user` WHERE username='creator01'));