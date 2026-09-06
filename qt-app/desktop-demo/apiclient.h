#ifndef APICLIENT_H
#define APICLIENT_H
#include <QObject>
#include <QJsonValue>
#include <QNetworkAccessManager>
#include <functional>

// 轻量 REST 客户端: 登录态 token + 常用方法(GET/POST/PATCH), JSON 收发
class ApiClient : public QObject {
    Q_OBJECT
public:
    static ApiClient *inst();
    void setBase(const QString &b) { m_base = b; }
    QString base() const { return m_base; }
    void setToken(const QString &t) { m_token = t; }
    QString token() const { return m_token; }
    QString lastError() const { return m_lastError; }

    using Cb = std::function<void(int code, const QJsonValue &data)>;
    void login(const QString &user, const QString &pwd, Cb cb);
    void get(const QString &path, Cb cb);
    void post(const QString &path, const QJsonObject &body, Cb cb);
    void patch(const QString &path, const QJsonObject &body, Cb cb);

private:
    ApiClient() = default;
    void send(const QString &method, const QString &path,
              const QJsonObject *body, Cb cb);
    QString m_base = QStringLiteral("http://127.0.0.1:8080");
    QString m_token;
    QString m_lastError;
    QNetworkAccessManager m_mgr;
};
#endif