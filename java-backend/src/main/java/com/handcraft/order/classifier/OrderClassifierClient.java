package com.handcraft.order.classifier;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Python 智能分类模块调用器。
 *
 * 设计决策(见 README 架构说明): Python 以【本地脚本】形式运行,
 * Java 通过 ProcessBuilder 启动子进程调用 —— 不部署独立 Python 服务,
 * 避免"本地脚本还要起 HTTP 服务"的架构矛盾。
 *
 * 约定: python/order_classifier.py 最后一行向 stdout 输出一行 JSON,
 * 字段与 classify() 返回一致: order_type / duration_days / estimated_complete_date ...
 */
@Component
public class OrderClassifierClient {

    @Value("${classifier.python-command:python}")
    private String pythonCommand;

    @Value("${classifier.script-path:../python/order_classifier.py}")
    private String scriptPath;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 调用智能分类: 识别订单类型 + 预估工期 + 预估完成日期
     * @param description 产品名称/描述/定制要求
     * @param quantity    数量
     * @return 分类结果 JSON 节点
     */
    public JsonNode classify(String description, int quantity) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    pythonCommand, scriptPath, description, String.valueOf(quantity));
            pb.redirectErrorStream(true);
            Process process = pb.start();

            StringBuilder stdout = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    stdout.append(line).append('\n');
                }
            }
            int exit = process.waitFor();
            String output = stdout.toString().trim();
            if (exit != 0 || output.isEmpty()) {
                throw new IllegalStateException(
                        "智能分类脚本执行失败 exit=" + exit + " output=" + output);
            }
            // 脚本输出为多行 JSON(缩进格式), 整体解析; 兜底取最后一行
            try {
                return objectMapper.readTree(output);
            } catch (Exception e) {
                String lastLine = output.substring(output.lastIndexOf('\n') + 1);
                return objectMapper.readTree(lastLine);
            }
        } catch (Exception e) {
            throw new IllegalStateException("调用智能分类模块失败", e);
        }
    }

    /** 批量调用示例(可后续替换为批量行处理, 当前业务为单条逐调) */
    public List<JsonNode> classifyBatch(List<String> descriptions, int quantity) {
        return descriptions.stream().map(d -> classify(d, quantity)).toList();
    }
}