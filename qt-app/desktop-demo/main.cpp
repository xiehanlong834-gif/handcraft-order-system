#include <QApplication>
#include <QDialog>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QFont>
#include <QJsonObject>
#include <QLabel>
#include <QTimer>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>

#include "apiclient.h"
#include "mainwindow.h"

// 注册对话框: 公开自助注册(仅客户角色, 后端强制)
class RegisterDialog : public QDialog {
public:
    RegisterDialog(QWidget *parent = nullptr) : QDialog(parent) {
        setWindowTitle("注册新账号 - 独立手作创作者订单管理系统");
        auto *lay = new QFormLayout(this);
        m_nick = new QLineEdit(this); m_nick->setPlaceholderText("称呼/昵称(必填), 如: 小鱼手作粉");
        m_phone = new QLineEdit(this); m_phone->setPlaceholderText("手机号(选填)");
        m_user = new QLineEdit(this); m_user->setPlaceholderText("3-20位字母/数字/下划线");
        m_pwd = new QLineEdit(this); m_pwd->setPlaceholderText("至少 6 位");
        m_pwd->setEchoMode(QLineEdit::Password);
        lay->addRow("称呼:", m_nick);
        lay->addRow("手机号:", m_phone);
        lay->addRow("用户名:", m_user);
        lay->addRow("密码:", m_pwd);
        m_status = new QLabel("注册后将自动成为「客户」角色, 可提交定制与追踪订单", this);
        m_status->setWordWrap(true);
        lay->addRow(m_status);
        auto *bb = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
        bb->button(QDialogButtonBox::Ok)->setText("注册");
        bb->button(QDialogButtonBox::Cancel)->setText("取消");
        lay->addRow(bb);
        connect(bb, &QDialogButtonBox::accepted, this, &RegisterDialog::tryReg);
        connect(bb, &QDialogButtonBox::rejected, this, &QDialog::reject);
    }
    QString username() const { return m_user->text().trimmed(); }
    QString password() const { return m_pwd->text(); }

private:
    void tryReg() {
        if (m_user->text().trimmed().isEmpty() || m_pwd->text().isEmpty() || m_nick->text().trimmed().isEmpty()) {
            m_status->setText("请完整填写称呼/用户名/密码");
            return;
        }
        m_status->setText("注册中...");
        ApiClient::inst()->post("/api/auth/register",
            QJsonObject{{"username", m_user->text().trimmed()}, {"password", m_pwd->text()},
                        {"nickname", m_nick->text().trimmed()}, {"phone", m_phone->text().trimmed()}},
            [this](int code, const QJsonValue &d) {
                if (code != 200) {
                    m_status->setText("注册失败: " + ApiClient::inst()->lastError());
                    return;
                }
                m_status->setText(d.toObject().value("message").toString());
                accept();
            });
    }
    QLineEdit *m_nick = nullptr, *m_phone = nullptr, *m_user = nullptr, *m_pwd = nullptr;
    QLabel *m_status = nullptr;
};

// 登录对话框: 演示账号 creator01/admin01/finance01/xiaolin/may, 密码 123456
class LoginDialog : public QDialog {
public:
    LoginDialog(const QString &user = "creator01", const QString &pwd = "123456",
                QWidget *parent = nullptr) : QDialog(parent) {
        setWindowTitle("登录 - 独立手作创作者订单管理系统");
        auto *lay = new QFormLayout(this);
        m_user = new QLineEdit(user, this);
        m_pwd = new QLineEdit(pwd, this);
        m_pwd->setEchoMode(QLineEdit::Password);
        lay->addRow("账号:", m_user);
        lay->addRow("密码:", m_pwd);
        m_status = new QLabel("提示: 演示账号 creator01 / admin01 / finance01 / xiaolin / may", this);
        m_status->setWordWrap(true);
        lay->addRow(m_status);
        auto *bb = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
        bb->button(QDialogButtonBox::Ok)->setText("登录");
        bb->button(QDialogButtonBox::Cancel)->setText("退出");
        lay->addRow(bb);
        connect(bb, &QDialogButtonBox::accepted, this, &LoginDialog::tryLogin);
        connect(bb, &QDialogButtonBox::rejected, this, &QDialog::reject);
        auto *reg = new QPushButton("没有账号？注册新账号", this);
        reg->setCursor(Qt::PointingHandCursor);
        reg->setStyleSheet("QPushButton{border:none;color:#1d4ed8;background:transparent;font-size:12px;}"
                           "QPushButton:hover{color:#1e40af;}");
        connect(reg, &QPushButton::clicked, this, [this]() {
            RegisterDialog d(this);
            if (d.exec() == QDialog::Accepted) {
                m_user->setText(d.username());
                m_pwd->setText(d.password());
                m_status->setText("注册成功！账号已自动填入, 点击「登录」即可进入");
            }
        });
        lay->addRow(reg);
    }

public:
    void tryLoginNow() { tryLogin(); }

private:
    void tryLogin() {
        m_status->setText("正在登录...");
        ApiClient::inst()->login(m_user->text().trimmed(), m_pwd->text(), [this](int code, const QJsonValue &d) {
            if (code != 200) {
                m_status->setText("登录失败: " + ApiClient::inst()->lastError());
                return;
            }
            const QJsonObject o = d.toObject();
            ApiClient::inst()->setToken(o.value("token").toString());
            m_role = o.value("user").toObject().value("roleCode").toString();
            m_name = o.value("user").toObject().value("realName").toString();
            accept();
        });
    }

    QLineEdit *m_user = nullptr;
    QLineEdit *m_pwd = nullptr;
    QLabel *m_status = nullptr;
    QString m_role, m_name;
    friend int runApp(int argc, char *argv[]);
};

static const char *kStyle = R"QSS(
/* ============================================================
 * vllm-hust-website 风格 · 蓝白主题
 * (借鉴 vLLM-HUST/vllm-hust-website 的设计语言:
 *  浅蓝画布 #f7fbff / 纯白面板 / slate 墨 #0f172a /
 *  主蓝 #1d4ed8 / 天青 #0ea5e9 / 细分隔线 #dbe7f3)
 * ============================================================ */
QWidget { font-size: 13px; color: #0f172a; }
QMainWindow, QDialog { background: #f7fbff; }
QStackedWidget { background: #f7fbff; }
QStackedWidget > QWidget { background: #f7fbff; }

/* 左侧导航: 白底面板 + 蓝色激活胶囊(vllm-hust site-nav 语言) */
#sidebar { background: #ffffff; border: none; border-right: 1px solid #dbe7f3;
           outline: 0; padding: 10px 6px; }
#sidebar::item { color: #475569; padding-left: 18px; border: none;
                 border-left: 3px solid transparent; border-radius: 0px; }
#sidebar::item:hover:!selected { background: #f1f5f9; color: #0f172a; }
#sidebar::item:selected { background: #eef4ff; color: #1d4ed8;
                          border-left: 3px solid #1d4ed8; font-weight: 700; }

/* 卡片化表格: 白色圆角 + 淡蓝底 */
QTableWidget { background: #ffffff; border: 1px solid #dbe7f3; border-radius: 10px;
               gridline-color: #f1f6fc; alternate-background-color: #fbfdff; }
QTableWidget::item { padding: 5px 10px; }
QTableWidget::item:selected { background: #e5f2ff; color: #0f172a; }
QHeaderView::section { background: #f8fbff; border: none; border-bottom: 1px solid #dbe7f3;
                       padding: 9px; font-weight: 700; color: #64748b; }
QTableCornerButton::section { background: #f8fbff; border: none; }

/* 按钮: 白底灰边次按钮 / 主蓝 #1d4ed8 */
QPushButton { background: #ffffff; border: 1px solid #c7d6ea; border-radius: 8px;
              padding: 5px 16px; color: #1e293b; min-height: 20px; }
QPushButton:hover { background: #f1f6fd; border-color: #1d4ed8; color: #1d4ed8; }
QPushButton:pressed { background: #e5efff; }
QPushButton[objectName="primary"] { background: #1d4ed8; border-color: #1d4ed8; color: #ffffff; font-weight: 600; }
QPushButton[objectName="primary"]:hover { background: #1e40af; border-color: #1e40af; color: #ffffff; }
QPushButton[objectName="primary"]:pressed { background: #172f8f; }

QGroupBox { background: #ffffff; border: 1px solid #dbe7f3; border-radius: 10px;
            margin-top: 16px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px;
                   color: #475569; font-weight: 600; }

QLineEdit, QTextEdit, QComboBox { background: #ffffff; border: 1px solid #c7d6ea;
                                  border-radius: 8px; padding: 5px 10px; }
QLineEdit:focus, QTextEdit:focus { border: 1px solid #1d4ed8; }
QComboBox { padding: 4px 10px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd9ea; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #9fb6d4; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #cbd9ea; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #9fb6d4; }

/* 状态栏: 白色 + 顶部分隔线(site-shell 观感) */
#statusbar { background: #ffffff; border-top: 1px solid #dbe7f3;
             padding: 5px 14px; color: #64748b; }
QLabel { background: transparent; }
QMessageBox { background: #ffffff; }
)QSS";

int runApp(int argc, char *argv[]) {
    QApplication app(argc, argv);
    QFont f(QStringLiteral("Microsoft YaHei"), 10);
    app.setFont(f);
    app.setStyle("Fusion");
    app.setStyleSheet(QString::fromUtf8(kStyle));
    ApiClient::inst()->setBase("http://127.0.0.1:8080");

    QString user = argc > 1 ? QString::fromUtf8(argv[1]) : QString();
    QString pwd = argc > 2 ? QString::fromUtf8(argv[2]) : QStringLiteral("123456");
    LoginDialog dlg(user.isEmpty() ? "creator01" : user, pwd);
    if (!user.isEmpty()) {
        // 自动登录模式(演示/脚本): 等对话框显示后自动提交
        QTimer::singleShot(300, &dlg, &LoginDialog::tryLoginNow);
    }
    if (dlg.exec() != QDialog::Accepted) return 0;

    MainWindow w(dlg.m_role, dlg.m_name);
    w.show();
    return app.exec();
}

int main(int argc, char *argv[]) { return runApp(argc, argv); }