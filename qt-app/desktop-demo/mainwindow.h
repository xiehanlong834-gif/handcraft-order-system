#ifndef MAINWINDOW_H
#define MAINWINDOW_H
#include <QMainWindow>
#include <QJsonArray>
#include <QJsonObject>
#include <QStringList>

class QListWidget;
class QStackedWidget;
class QTableWidget;
class QLabel;
class QLineEdit;
class QTextEdit;

// 主窗口: 登录后按角色(creator/customer/admin/finance)渲染功能页签
class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    MainWindow(const QString &role, const QString &realName, QWidget *parent = nullptr);

private:
    // 通用小工具
    QTableWidget *makeTable(const QStringList &headers);
    void fillTable(QTableWidget *t, const QJsonArray &rows, const QStringList &keys);
    void toast(const QString &msg);          // 状态栏消息
    void showError();                        // 显示 ApiClient 最近错误
    QString askText(const QString &title, const QString &label);

    // 页面构建
    QWidget *buildCustomerPage();
    QWidget *buildAdminPage();
    QWidget *buildFinancePage();

    // 数据刷新(创作者)
    void refreshOrders();
    void refreshMaterials();
    void refreshCustomers();
    void refreshReminderBanner();
    // 数据刷新(客户)
    void refreshMyOrders();
    // 数据刷新(管理员/财务)
    void refreshAdminOverview();
    void refreshUsers();
    void refreshFinance();

    // 业务操作(创作者)
    void createOrder();
    void advanceOrder();
    void registerMaterialUsage();
    void setLaborCost();
    void archiveOrder();
    void stockInOut(bool isIn);
    void createMaterial();
    void createCustomer();
    // 客户操作
    void submitCustomRequest();
    // 管理员操作
    void createUser();
    void publishAnnouncement();
    // 财务: 报表查看已在 refreshFinance 内

    QString m_role;
    QLabel *m_status = nullptr;
    QLabel *m_reminder = nullptr;
    QListWidget *m_nav = nullptr;
    QStackedWidget *m_stack = nullptr;
    void addPage(const QString &title, QWidget *page);

    QTableWidget *m_orders = nullptr;
    QTableWidget *m_materials = nullptr;
    QTableWidget *m_customers = nullptr;
    QTableWidget *m_myOrders = nullptr;
    QTableWidget *m_users = nullptr;
    QTableWidget *m_trend = nullptr;
    QTableWidget *m_repurchase = nullptr;
    QTableWidget *m_consumption = nullptr;
    QLabel *m_overview = nullptr;
    QLabel *m_finSummary = nullptr;
    QLabel *m_customerPhone = nullptr;
};
#endif