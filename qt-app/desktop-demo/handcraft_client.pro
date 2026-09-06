# 独立手作创作者订单管理系统 —— Qt 桌面演示客户端(Windows/MinGW)
# 同一套 Widgets/网络层代码可迁移 Android(需 Qt for Android + Android SDK)
# 构建: qmake && mingw32-make   (PATH 需含 Qt bin 与 MinGW bin)
QT += core gui widgets network
CONFIG += c++17
TARGET = handcraft_client
TEMPLATE = app
SOURCES += main.cpp apiclient.cpp mainwindow.cpp
HEADERS += apiclient.h mainwindow.h