
"use client";
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function BookmarkletSetup() {
  // 生成书签代码：加载远程 JS 并执行
  // 注意：实际生产中 localhost 应替换为您的真实域名
  const scriptUrl = "http://localhost:3000/rpa-bookmarklet.js"; 
  const bookmarkHref = `javascript:(function(){var s=document.createElement('script');s.src='${scriptUrl}?t='+new Date().getTime();document.body.appendChild(s);})();`;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">全自动发布助手 (免安装版)</h1>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>步骤 1：安装助手</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">
              请将下方的蓝色按钮，用鼠标 <b>拖拽</b> 到浏览器的 <b>书签收藏栏</b> 中。
            </p>
            <div className="flex justify-center p-6 border-2 border-dashed rounded-lg bg-gray-50">
              {/* 这是一个特殊的链接，拖动它就是添加书签 */}
              <a 
                href={bookmarkHref}
                className="px-6 py-3 bg-blue-600 text-white font-bold rounded-full hover:bg-blue-700 shadow-lg cursor-grab active:cursor-grabbing"
                onClick={(e) => e.preventDefault()} // 防止点击跳转
                title="拖动我到书签栏"
              >
                GlobalPilot RPA
              </a>
            </div>
            <p className="text-sm text-gray-400">
              注意：如果您的浏览器没有显示书签栏，请按 <kbd>Ctrl+Shift+B</kbd> (Windows) 或 <kbd>Cmd+Shift+B</kbd> (Mac) 打开。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>步骤 2：如何使用</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ol className="list-decimal list-inside space-y-2 text-gray-700">
              <li>在任务中心点击 <b>“一键发布”</b> 按钮。</li>
              <li>系统会自动并在新标签页打开 <b>小红书创作中心</b>。</li>
              <li>等待页面加载完毕（如有登录弹窗，请先登录）。</li>
              <li>点击浏览器书签栏上的 <b>GlobalPilot RPA</b>。</li>
              <li>见证奇迹：标题和正文会自动填充！</li>
            </ol>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 p-4 bg-yellow-50 text-yellow-800 rounded border border-yellow-200">
        <h3 className="font-bold">为什么使用书签脚本？</h3>
        <p className="text-sm mt-1">
          由于浏览器安全限制，网页无法直接操作其他网站。书签脚本是最安全的“轻量级辅助”方案，
          <b>无需下载任何软件或插件</b>，完全利用浏览器原生功能，且不会被平台判定为外挂风险。
        </p>
      </div>
    </div>
  );
}
