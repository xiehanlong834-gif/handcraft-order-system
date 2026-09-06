#include "apiclient.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QUrlQuery>

ApiClient *ApiClient::inst() {
    static ApiClient c;
    return &c;
}

void ApiClient::send(const QString &method, const QString &path,
                     const QJsonObject *body, Cb cb) {
    QNetworkRequest req(QUrl(m_base + path));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_token.isEmpty())
        req.setRawHeader("Authorization", ("Bearer " + m_token).toUtf8());
    QNetworkReply *reply = nullptr;
    if (method == "GET") reply = m_mgr.get(req);
    else if (method == "POST") reply = m_mgr.post(req, body ? QJsonDocument(*body).toJson() : QByteArray("{}"));
    else reply = m_mgr.sendCustomRequest(req, method.toUtf8(),
                                         body ? QJsonDocument(*body).toJson() : QByteArray());
    connect(reply, &QNetworkReply::finished, this, [this, reply, cb]() {
        int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        QByteArray raw = reply->readAll();
        m_lastError.clear();
        QJsonValue data;
        if (!raw.isEmpty()) {
            QJsonParseError err;
            QJsonDocument doc = QJsonDocument::fromJson(raw, &err);
            if (err.error == QJsonParseError::NoError)
                data = doc.isObject() ? QJsonValue(doc.object()) : QJsonValue(doc.array());
            else
                m_lastError = QString::fromUtf8(raw).left(200);
        }
        if (code >= 400) {
            if (data.isObject())
                m_lastError = data.toObject().value("message").toString();
            if (m_lastError.isEmpty()) m_lastError = QStringLiteral("HTTP %1").arg(code);
        }
        cb(code, data);
        reply->deleteLater();
    });
}

void ApiClient::login(const QString &user, const QString &pwd, Cb cb) {
    send("POST", "/api/auth/login",
         new QJsonObject{{"username", user}, {"password", pwd}}, cb);
}

void ApiClient::get(const QString &path, Cb cb) { send("GET", path, nullptr, cb); }
void ApiClient::post(const QString &path, const QJsonObject &body, Cb cb) { send("POST", path, &body, cb); }
void ApiClient::patch(const QString &path, const QJsonObject &body, Cb cb) { send("PATCH", path, &body, cb); }