"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Download, Monitor } from "lucide-react";
import { useToast } from "@/contexts/ToastContext";
import { PageHeader } from "@/components/PageHeader";

// 模拟配置生成 - 实际项目中应从 API 获取当前用户的 Token
const generateConfig = () => {
    // 优先使用环境变量中的 API 地址，否则回退 to hardcoded production value to fix user issue
    // removing trailing slash if present to avoid double slash with /api/v1
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    // Fallback logic improved: if env is missing, use default dev URL
    const baseUrl = (envUrl || "http://localhost:8010").replace(/\/$/, "");

    return {
        "GEO_SERVER_URL": `${baseUrl}/api/v1`, 
        "WORKER_ID": "client_placeholder", // 初始占位符，避免 hydration mismatch
        "WORKER_SECRET": "geo-rpa-secret-2026", 
        "RPA_HEADLESS": "false",
        "RPA_BROWSER": "chromium"
    };
};

export default function ClientDownloadPage() {
    // 使用固定的初始配置，不再重新生成导致抖动
    // 只有 WORKER_ID 需要唯一，我们在 useEffect 中只更新它
    const [config, setConfig] = useState(generateConfig());
    const [downloaded, setDownloaded] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const { showToast } = useToast();

    // 在客户端挂载后生成随机 ID
    // 仅执行一次，且只更新 ID 部分，避免整个对象引用变化导致莫名重绘
    useEffect(() => {
        // 生成唯一 ID
        const uniqueId = `client_${Math.random().toString(36).substr(2, 6)}`;
        setConfig(prev => {
            // 如无变化则不更新，React 18自动批处理
            if (prev.WORKER_ID !== 'client_placeholder') return prev;
            return { ...prev, "WORKER_ID": uniqueId };
        });
    }, []);

    const handleCopyConfig = () => {
        navigator.clipboard.writeText(JSON.stringify(config, null, 4));
        showToast("配置已复制，请创建 config.json 并粘贴", "success");
    };

    const handleDownloadConfig = () => {
        const element = document.createElement("a");
        const file = new Blob([JSON.stringify(config, null, 4)], {type: 'application/json'});
        element.href = URL.createObjectURL(file);
        element.download = "config.json";
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        showToast("配置文件下载成功", "success");
    };

    const handleWakeProtocol = () => {
        showToast("正在请求系统唤起客户端...", "info");
        // 使用 iframe 方式避免页面跳转/刷新，且对用户更友好
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = 'digitalemployee://wake';
        document.body.appendChild(iframe);
        setTimeout(() => {
            document.body.removeChild(iframe);
        }, 3000);
    };

    return (
        <div className="container mx-auto py-10 max-w-5xl">
            <PageHeader
                title="RPA 客户端部署"
                description="在您的本地电脑运行数字员工，安全、稳定、零封号风险。"
                className="mb-8"
            />

            <div className="max-w-xl mx-auto">
                <Card className="relative overflow-hidden">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Monitor className="h-5 w-5"/>
                            下载主程序
                        </CardTitle>
                        <CardDescription>
                            Windows 64位 独立运行包 (v1.0.0)
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-text-tertiary mb-4">
                            包含了所有必要的运行环境。无需安装 Python，解压即用。
                        </p>
                        <Alert className="border-accent mb-4">
                            <AlertDescription className="text-xs text-text-secondary">
                                环境要求：Windows 10/11, 建议 8G 内存以上
                            </AlertDescription>
                            <AlertDescription className="text-xs text-text-secondary">
                                下载后点击运行的下载文件：DigitalEmployeeRPA.exe
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                    <CardFooter>
                        <Button 
                            className="w-full" 
                            size="lg"
                            disabled={downloading}
                            onClick={() => {
                                showToast("开始下载客户端...", "info");
                                setDownloading(true);
                                
                                // use hidden iframe to download file to prevent page jitter/reload
                                const iframe = document.createElement('iframe');
                                iframe.style.display = 'none';
                                iframe.src = '/downloads/DigitalEmployeeRPA.exe';
                                document.body.appendChild(iframe);
                                
                                // Mock finish state just for UX feeling (since we can't track real download progress via iframe)
                                setTimeout(() => {
                                    setDownloaded(true);
                                    setDownloading(false);
                                    document.body.removeChild(iframe);
                                    showToast("下载任务已开始，请留意浏览器下载栏", "success");
                                }, 2000);
                            }}
                        >
                            {downloading ? (
                                <>
                                 <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-separator mr-2"></div>
                                 请求中...
                                </>
                            ) : (
                                <>
                                <Download className="mr-2 h-4 w-4" /> 
                                下载客户端 (.exe)
                                </>
                            )}
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
