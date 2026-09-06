#include "mainwindow.h"
#include "apiclient.h"

#include <QApplication>
#include <QBoxLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QInputDialog>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QListWidget>
#include <QSize>
#include <QSize>
#include <QStackedWidget>
#include <QTableWidget>
#include <QTextEdit>
#include <QJsonDocument>

using Api = ApiClient;

// ==================== 通用小工具 ====================
QTableWidget *MainWindow::makeTable(const QStringList &headers) {
    auto *t = new QTableWidget(0, headers.size());
    t->setHorizontalHeaderLabels(headers);
    t->horizontalHeader()->setStretchLastSection(true);
    t->setSelectionBehavior(QAbstractItemView::SelectRows);
    t->setEditTriggers(QAbstractItemView::NoEditTriggers);
    t->verticalHeader()->setVisible(false);
    return t;
}

void MainWindow::fillTable(QTableWidget *t, const QJsonArray &rows, const QStringList &keys) {
    t->setRowCount(rows.size());
    for (int r = 0; r < rows.size(); ++r) {
        const QJsonObject o = rows.at(r).toObject();
        for (int c = 0; c < keys.size(); ++c) {
            const QJsonValue v = o.value(keys.at(c));
            QString s;
            if (v.isDouble()) s = QString::number(v.toDouble(), 'f', v.toDouble() == qint64(v.toDouble()) ? 0 : 2);
            else if (v.isBool()) s = v.toBool() ? "是" : "否";
            else if (!v.isNull()) s = v.toString();
            auto *item = new QTableWidgetItem(s);
            if (v.isDouble()) item->setTextAlignment(Qt::AlignRight | Qt::AlignVCenter);
            t->setItem(r, c, item);
        }
    }
    t->resizeColumnsToContents();
}

void MainWindow::toast(const QString &msg) {
    if (m_status) m_status->setText(msg);
    QApplication::processEvents();
}

void MainWindow::showError() {
    const QString e = Api::inst()->lastError();
    toast(e.isEmpty() ? "请求失败" : e);
}

QString MainWindow::askText(const QString &title, const QString &label) {
    bool ok = false;
    const QString v = QInputDialog::getText(this, title, label, QLineEdit::Normal, QString(), &ok);
    return ok ? v.trimmed() : QString();
}

// ==================== 构造: 按角色组页 ====================
MainWindow::MainWindow(const QString &role, const QString &realName, QWidget *parent)
    : QMainWindow(parent), m_role(role) {
    setWindowTitle(QStringLiteral("独立手作创作者订单管理系统 —— %1(%2)").arg(realName, role));
    resize(1080, 640);

    auto *central = new QWidget(this);
    auto *lay = new QVBoxLayout(central);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(0);
    auto *body = new QHBoxLayout();
    body->setContentsMargins(0, 0, 0, 0);
    body->setSpacing(0);
    m_nav = new QListWidget(central);
    m_nav->setObjectName("sidebar");
    m_nav->setFixedWidth(172);
    body->addWidget(m_nav);
    m_stack = new QStackedWidget(central);
    body->addWidget(m_stack, 1);
    lay->addLayout(body);

    if (role == "creator") {
        QWidget *page = new QWidget(this);
        auto *pl = new QVBoxLayout(page);
        m_reminder = new QLabel(page);
        m_reminder->setStyleSheet("background:#e5f2ff;color:#1d4ed8;padding:8px 12px;border:1px solid #bfdbfe;border-radius:8px;font-weight:600;");
        pl->addWidget(m_reminder);
        m_orders = makeTable({"ID","订单号","客户","产品","类型","数量","状态","收入","利润","截止日期"});
        pl->addWidget(m_orders);
        auto *hb = new QHBoxLayout();
        for (const QString &txt : {"刷新", "新建订单(自动分类)", "推进状态", "登记耗料", "录入工时", "取消/归档"}) {
            auto *b = new QPushButton(txt, page);
            hb->addWidget(b);
            if (txt == "刷新") connect(b, &QPushButton::clicked, this, &MainWindow::refreshOrders);
            else if (txt == "新建订单(自动分类)") connect(b, &QPushButton::clicked, this, &MainWindow::createOrder);
            else if (txt == "推进状态") connect(b, &QPushButton::clicked, this, &MainWindow::advanceOrder);
            else if (txt == "登记耗料") connect(b, &QPushButton::clicked, this, &MainWindow::registerMaterialUsage);
            else if (txt == "录入工时") connect(b, &QPushButton::clicked, this, &MainWindow::setLaborCost);
            else connect(b, &QPushButton::clicked, this, &MainWindow::archiveOrder);
        }
        pl->addLayout(hb);
        addPage("订单", page);

        auto *mp = new QWidget(this); auto *ml = new QVBoxLayout(mp);
        m_materials = makeTable({"ID","材料","规格","单位","库存","预警阈值","单价","品类"});
        ml->addWidget(m_materials);
        auto *mb = new QHBoxLayout();
        for (const QString &txt : {"刷新", "入库", "出库"}) {
            auto *b = new QPushButton(txt, mp);
            mb->addWidget(b);
            if (txt == "刷新") connect(b, &QPushButton::clicked, this, &MainWindow::refreshMaterials);
            else if (txt == "入库") connect(b, &QPushButton::clicked, this, [this]{ stockInOut(true); });
            else connect(b, &QPushButton::clicked, this, [this]{ stockInOut(false); });
        }
        ml->addLayout(mb);
        addPage("库存", mp);

        auto *cp = new QWidget(this); auto *cl = new QVBoxLayout(cp);
        m_customers = makeTable({"ID","称呼","电话(脱敏)","标签","订单数","已完成"});
        cl->addWidget(m_customers);
        auto *cb = new QHBoxLayout();
        for (const QString &txt : {"刷新", "新增客户"}) {
            auto *b = new QPushButton(txt, cp);
            cb->addWidget(b);
            if (txt == "刷新") connect(b, &QPushButton::clicked, this, &MainWindow::refreshCustomers);
            else connect(b, &QPushButton::clicked, this, &MainWindow::createCustomer);
        }
        cl->addLayout(cb);
        addPage("客户", cp);
    } else if (role == "customer") {
        addPage("我的订单", buildCustomerPage());
    } else if (role == "admin") {
        addPage("管理后台", buildAdminPage());
    } else if (role == "finance") {
        addPage("经营报表", buildFinancePage());
    }

    m_status = new QLabel(QStringLiteral("就绪 · 后端 %1").arg(Api::inst()->base()), central);
    m_status->setObjectName("statusbar");
    lay->addWidget(m_status);
    setCentralWidget(central);

    connect(m_nav, &QListWidget::currentRowChanged, m_stack, &QStackedWidget::setCurrentIndex);

    if (role == "creator") { refreshOrders(); refreshMaterials(); refreshCustomers(); }
    else if (role == "customer") refreshMyOrders();
    else if (role == "admin") { refreshAdminOverview(); refreshUsers(); }
    else if (role == "finance") refreshFinance();
}
// ==================== 创作者: 数据刷新 ====================
void MainWindow::refreshReminderBanner() {
    Api::inst()->get("/api/orders/due-reminders", [this](int code, const QJsonValue &d) {
        if (code != 200) { m_reminder->setText("提醒: 加载失败(" + QString::number(code) + ")"); return; }
        const QJsonArray a = d.toArray();
        if (a.isEmpty()) { m_reminder->setText("工期提醒: 无 3 天内到期订单 ✓"); return; }
        QStringList parts;
        for (const auto &v : a) {
            const QJsonObject o = v.toObject();
            parts << QStringLiteral("%1 · %2 · 截止%3")
                         .arg(o.value("customerName").toString(), o.value("productName").toString(),
                              o.value("estimatedCompleteDate").toString());
        }
        m_reminder->setText("⏰ 工期提醒(" + QString::number(a.size()) + "): " + parts.join("  |  "));
    });
}

void MainWindow::refreshOrders() {
    toast("加载订单...");
    Api::inst()->get("/api/orders", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_orders, d.toArray(),
                  {"orderId", "orderNo", "customerName", "productName", "orderType",
                   "quantity", "status", "income", "profit", "estimatedCompleteDate"});
        toast(QStringLiteral("订单 %1 条").arg(m_orders->rowCount()));
        refreshReminderBanner();
    });
}

void MainWindow::refreshMaterials() {
    Api::inst()->get("/api/materials", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_materials, d.toArray(),
                  {"materialId", "name", "spec", "unit", "stockQty",
                   "lowStockThreshold", "unitPrice", "materialCategory"});
    });
}

void MainWindow::refreshCustomers() {
    Api::inst()->get("/api/customers", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_customers, d.toArray(),
                  {"customerId", "name", "phoneMasked", "tags", "orderCount", "completedCount"});
    });
}

// ==================== 创作者: 业务操作 ====================
void MainWindow::createOrder() {
    const QString customer = askText("新建订单", "客户ID(现有客户, 如 1/2):");
    const QString product = askText("新建订单", "产品名称/描述(含定制/现货/批量等关键词将自动分类):");
    if (customer.isEmpty() || product.isEmpty()) return;
    bool ok = false;
    const double price = QInputDialog::getDouble(this, "新建订单", "单价:", 100, 0, 1000000, 2, &ok);
    if (!ok) return;
    Api::inst()->post("/api/orders",
        QJsonObject{{"customerId", customer.toLongLong()}, {"productName", product},
                    {"requirement", product}, {"quantity", 1}, {"unitPrice", price}},
        [this](int code, const QJsonValue &d) {
            if (code != 200) { showError(); return; }
            const QJsonObject o = d.toObject();
            const QJsonObject clz = o.value("classify").toObject();
            QMessageBox::information(this, "智能分类结果",
                QStringLiteral("订单 #%1 创建成功\n类型: %2\n预估工期: %3 天\n预估完成: %4\n%5")
                    .arg(o.value("orderId").toVariant().toString())
                    .arg(clz.value("orderTypeLabel").toString())
                    .arg(clz.value("estimateDays").toInt())
                    .arg(clz.value("estimatedCompleteDate").toString())
                    .arg(o.value("warn").toString()));
            refreshOrders();
        });
}

void MainWindow::advanceOrder() {
    const int row = m_orders->currentRow();
    if (row < 0) { toast("请先选中一个订单"); return; }
    const auto o = m_orders->item(row, 0);
    const auto s = m_orders->item(row, 6);
    if (!o || !s) return;
    const QString next = s->text() == "PENDING_CONFIRM" ? "IN_PRODUCTION"
                       : s->text() == "IN_PRODUCTION" ? "PENDING_SHIPMENT"
                       : s->text() == "PENDING_SHIPMENT" ? "COMPLETED" : "";
    if (next.isEmpty()) { toast("当前状态不可推进(已完成/取消/归档)"); return; }
    Api::inst()->patch("/api/orders/" + o->text() + "/status",
                       QJsonObject{{"toStatus", next}, {"note", "Qt 客户端推进"}},
        [this](int code, const QJsonValue &d) {
            if (code != 200) { showError(); return; }
            toast(d.toObject().value("message").toString());
            refreshOrders();
        });
}

void MainWindow::registerMaterialUsage() {
    const int row = m_orders->currentRow();
    if (row < 0) { toast("请先选中订单"); return; }
    const QString oid = m_orders->item(row, 0)->text();
    const QString mid = askText("登记耗料", "材料ID(见库存页):");
    const QString qty = askText("登记耗料", "耗用数量:");
    if (mid.isEmpty() || qty.isEmpty()) return;
    Api::inst()->post("/api/orders/" + oid + "/materials",
                      QJsonObject{{"materialId", mid.toLongLong()}, {"quantityUsed", qty.toDouble()}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("耗料登记成功(库存已扣减, 成本已刷新)");
            refreshOrders(); refreshMaterials();
        });
}

void MainWindow::setLaborCost() {
    const int row = m_orders->currentRow();
    if (row < 0) { toast("请先选中订单"); return; }
    const QString oid = m_orders->item(row, 0)->text();
    const QString v = askText("录入工时成本", "工时成本(元):");
    if (v.isEmpty()) return;
    Api::inst()->post("/api/orders/" + oid + "/labor-cost",
                      QJsonObject{{"laborCost", v.toDouble()}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("工时成本已保存");
            refreshOrders();
        });
}

void MainWindow::archiveOrder() {
    const int row = m_orders->currentRow();
    if (row < 0) { toast("请先选中订单"); return; }
    const auto o = m_orders->item(row, 0);
    const auto s = m_orders->item(row, 6);
    if (!o || !s) return;
    const QString path = (s->text() == "COMPLETED" || s->text() == "CANCELLED")
                         ? "/api/orders/" + o->text() + "/archive"
                         : "/api/orders/" + o->text() + "/cancel";
    Api::inst()->post(path, QJsonObject{}, [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        toast(d.toObject().value("message").toString());
        refreshOrders();
    });
}

void MainWindow::stockInOut(bool isIn) {
    const int row = m_materials->currentRow();
    if (row < 0) { toast("请先在库存页选中材料"); return; }
    const QString mid = m_materials->item(row, 0)->text();
    const QString qty = askText(isIn ? "入库" : "出库", "数量:");
    if (qty.isEmpty()) return;
    Api::inst()->post(QStringLiteral("/api/materials/%1/%2").arg(mid, isIn ? "in" : "out"),
                      QJsonObject{{"quantity", qty.toDouble()}, {"note", "Qt 客户端"}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("操作成功");
            refreshMaterials();
        });
}

void MainWindow::createCustomer() {
    const QString name = askText("新增客户", "称呼:");
    const QString phone = askText("新增客户", "手机号:");
    if (name.isEmpty()) return;
    Api::inst()->post("/api/customers",
                      QJsonObject{{"name", name}, {"phone", phone}, {"tags", "Qt新增"}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("客户已添加");
            refreshCustomers();
        });
}
// ==================== 客户页 ====================
QWidget *MainWindow::buildCustomerPage() {
    auto *page = new QWidget(this);
    auto *lay = new QVBoxLayout(page);
    m_myOrders = makeTable({"ID", "订单号", "产品", "类型", "数量", "状态", "金额", "预计完成"});
    lay->addWidget(m_myOrders);

    auto *form = new QGroupBox("提交定制需求(创新点: 自动分类+工期)", page);
    auto *fl = new QVBoxLayout(form);
    auto *product = new QLineEdit(form); product->setPlaceholderText("产品名称/描述, 如: 定制刻字手镯");
    auto *requirement = new QLineEdit(form); requirement->setPlaceholderText("定制要求(专属/按需等描述)");
    auto *qty = new QLineEdit(form); qty->setPlaceholderText("数量");
    auto *submit = new QPushButton("提交定制", form); submit->setObjectName("primary");
    fl->addWidget(new QLabel("产品:", form)); fl->addWidget(product);
    fl->addWidget(new QLabel("定制要求:", form)); fl->addWidget(requirement);
    fl->addWidget(new QLabel("数量:", form)); fl->addWidget(qty);
    fl->addWidget(submit);
    lay->addWidget(form);
    connect(submit, &QPushButton::clicked, this, [this, product, requirement, qty]() {
        Api::inst()->post("/api/my/custom-requests",
            QJsonObject{{"productName", product->text().trimmed()},
                        {"requirement", requirement->text().trimmed()},
                        {"quantity", qty->text().toInt() > 0 ? qty->text().toInt() : 1},
                        {"unitPrice", 0}},
            [this](int code, const QJsonValue &d) {
                if (code != 200) { showError(); return; }
                const QJsonObject clz = d.toObject().value("classify").toObject();
                QMessageBox::information(this, "提交成功",
                    QStringLiteral("定制需求已提交, 等待创作者确认\n识别类型: %1 · 预估工期 %2 天")
                        .arg(clz.value("orderTypeLabel").toString())
                        .arg(clz.value("estimateDays").toInt()));
                refreshMyOrders();
            });
    });
    return page;
}

void MainWindow::refreshMyOrders() {
    Api::inst()->get("/api/my/orders", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_myOrders, d.toArray(),
                  {"orderId", "orderNo", "productName", "orderType", "quantity",
                   "status", "income", "estimatedCompleteDate"});
        toast(QStringLiteral("我的订单 %1 条").arg(m_myOrders->rowCount()));
    });
}

void MainWindow::submitCustomRequest() {
    // 实际逻辑在 buildCustomerPage 内(带表单), 此桩仅占位
}
// ==================== 管理员页 ====================
QWidget *MainWindow::buildAdminPage() {
    auto *page = new QWidget(this);
    auto *lay = new QVBoxLayout(page);
    m_overview = new QLabel("经营总览: 加载中...", page);
    m_overview->setStyleSheet("background:#eef4ff;color:#1d4ed8;padding:10px 14px;border:1px solid #dbe7f3;border-radius:8px;font-weight:600;");
    lay->addWidget(m_overview);

    m_users = makeTable({"ID", "用户名", "姓名", "电话(脱敏)", "角色", "状态"});
    lay->addWidget(m_users);
    auto *hb = new QHBoxLayout();
    for (const QString &txt : {"刷新", "新建用户", "发布公告"}) {
        auto *b = new QPushButton(txt, page);
        hb->addWidget(b);
        if (txt == "刷新") connect(b, &QPushButton::clicked, this, [this]{ refreshAdminOverview(); refreshUsers(); });
        else if (txt == "新建用户") connect(b, &QPushButton::clicked, this, &MainWindow::createUser);
        else connect(b, &QPushButton::clicked, this, &MainWindow::publishAnnouncement);
    }
    lay->addLayout(hb);
    return page;
}

void MainWindow::refreshAdminOverview() {
    Api::inst()->get("/api/admin/overview", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        const QJsonObject o = d.toObject();
        m_overview->setText(QStringLiteral(
            "经营总览  订单 %1 | 进行中 %2 | 已完成 %3 | 低库存材料 %4 | 临期订单 %5\n"
            "累计收入 ¥%6 | 成本 ¥%7 | 利润 ¥%8")
            .arg(o.value("totalOrders").toInt()).arg(o.value("inProgressOrders").toInt())
            .arg(o.value("completedOrders").toInt()).arg(o.value("lowStockMaterials").toInt())
            .arg(o.value("dueSoonOrders").toInt())
            .arg(o.value("totalIncome").toDouble(), 0, 'f', 2)
            .arg(o.value("totalCost").toDouble(), 0, 'f', 2)
            .arg(o.value("totalProfit").toDouble(), 0, 'f', 2));
    });
}

void MainWindow::refreshUsers() {
    Api::inst()->get("/api/admin/users", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_users, d.toArray(),
                  {"userId", "username", "realName", "phoneMasked", "roleName", "status"});
    });
}

void MainWindow::createUser() {
    const QString name = askText("新建用户", "用户名:");
    const QString pwd = askText("新建用户", "密码(>=6位):");
    const QString role = askText("新建用户", "角色码(creator/customer/admin/finance):");
    const QString real = askText("新建用户", "姓名:");
    if (name.isEmpty() || pwd.isEmpty()) return;
    Api::inst()->post("/api/admin/users",
        QJsonObject{{"username", name}, {"password", pwd}, {"roleCode", role}, {"realName", real}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("用户已创建(BCrypt 加密存储)");
            refreshUsers();
        });
}

void MainWindow::publishAnnouncement() {
    const QString title = askText("发布公告", "标题:");
    const QString content = askText("发布公告", "内容:");
    if (title.isEmpty()) return;
    Api::inst()->post("/api/admin/announcements",
                      QJsonObject{{"title", title}, {"content", content}},
        [this](int code, const QJsonValue &) {
            if (code != 200) { showError(); return; }
            toast("公告已发布");
        });
}

// ==================== 财务查看者页 ====================
QWidget *MainWindow::buildFinancePage() {
    auto *page = new QWidget(this);
    auto *lay = new QVBoxLayout(page);
    m_finSummary = new QLabel("收支总览: 加载中...", page);
    m_finSummary->setStyleSheet("background:#eef4ff;color:#1d4ed8;padding:10px 14px;border:1px solid #dbe7f3;border-radius:8px;font-weight:600;");
    lay->addWidget(m_finSummary);

    m_trend = makeTable({"期间", "订单数", "收入", "成本", "利润"});
    lay->addWidget(new QLabel("利润趋势(月):", page));
    lay->addWidget(m_trend);

    m_repurchase = makeTable({"客户", "单数", "累计消费", "价值分层"});
    lay->addWidget(new QLabel("客户复购(价值分层):", page));
    lay->addWidget(m_repurchase);

    m_consumption = makeTable({"材料", "品类", "消耗量", "消耗成本"});
    lay->addWidget(new QLabel("材料消耗分析:", page));
    lay->addWidget(m_consumption);

    auto *b = new QPushButton("刷新报表", page); b->setObjectName("primary");
    connect(b, &QPushButton::clicked, this, &MainWindow::refreshFinance);
    lay->addWidget(b);
    return page;
}

void MainWindow::refreshFinance() {
    Api::inst()->get("/api/reports/summary", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        const QJsonObject o = d.toObject();
        m_finSummary->setText(QStringLiteral(
            "收支总览  订单 %1 | 收入 ¥%2 | 成本 ¥%3 | 利润 ¥%4 (仅统计已完成/有效归档单)")
            .arg(o.value("totalOrders").toInt())
            .arg(o.value("income").toDouble(), 0, 'f', 2)
            .arg(o.value("cost").toDouble(), 0, 'f', 2)
            .arg(o.value("profit").toDouble(), 0, 'f', 2));
    });
    Api::inst()->get("/api/reports/profit-trend?group=month", [this](int code, const QJsonValue &d) {
        if (code == 200)
            fillTable(m_trend, d.toArray(), {"period", "orders", "income", "cost", "profit"});
        else showError();
    });
    Api::inst()->get("/api/reports/repurchase", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        const QJsonArray rows = d.toObject().value("customers").toArray();
        m_repurchase->setRowCount(rows.size());
        for (int r = 0; r < rows.size(); ++r) {
            const QJsonObject o = rows.at(r).toObject();
            m_repurchase->setItem(r, 0, new QTableWidgetItem(o.value("customerName").toString()));
            m_repurchase->setItem(r, 1, new QTableWidgetItem(o.value("orders").toVariant().toString()));
            m_repurchase->setItem(r, 2, new QTableWidgetItem(QString::number(o.value("totalSpend").toDouble(), 'f', 2)));
            m_repurchase->setItem(r, 3, new QTableWidgetItem(o.value("tier").toString()));
        }
        const QJsonObject tiers = d.toObject().value("valueTiers").toObject();
        m_finSummary->setText(m_finSummary->text() + QStringLiteral("\n复购率 %1% | 高价值 %2 人 | 中价值 %3 人")
            .arg(d.toObject().value("repurchaseRate").toDouble(), 0, 'f', 1)
            .arg(tiers.value("high").toObject().value("customers").toInt())
            .arg(tiers.value("medium").toObject().value("customers").toInt()));
    });
    Api::inst()->get("/api/reports/materials", [this](int code, const QJsonValue &d) {
        if (code != 200) { showError(); return; }
        fillTable(m_consumption, d.toObject().value("items").toArray(),
                  {"materialName", "materialCategory", "quantityUsed", "cost"});
    });
}

// 侧边导航 + 内容页
void MainWindow::addPage(const QString &title, QWidget *page) {
    auto *item = new QListWidgetItem(title, m_nav);
    item->setSizeHint(QSize(0, 40));
    m_nav->addItem(item);
    m_stack->addWidget(page);
    if (m_stack->count() == 1) m_nav->setCurrentRow(0);
}
