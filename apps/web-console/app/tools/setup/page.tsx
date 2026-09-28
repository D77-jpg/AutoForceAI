
"use client";
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/PageHeader";

export default function BookmarkletSetup() {
  // 书签脚本会在小红书/抖音等第三方页面里执行，相对路径会被解析成那个页面的域名，
  // 因此必须使用本控制台的绝对地址。origin 只能在浏览器中获取，放到挂载后再计算，
  // 避免预渲染出的 HTML 与客户端首帧不一致。
  const [scriptUrl, setScriptUrl] = useState('');
  useEffect(() => {
    setScriptUrl(`${window.location.origin}/rpa-bookmarklet.js`);
  }, []);
  const bookmarkHref = scriptUrl
    ? `javascript:(function(){var s=document.createElement('script');s.src='${scriptUrl}?t='+new Date().getTime();document.body.appendChild(s);})();`
    : '';

  return (
    <div className="apple-page max-w-4xl">
      <PageHeader
        title="全自动发布助手（免安装版）"
        description="通过浏览器书签脚本完成一键发布，无需安装任何插件。"
      />
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>步骤 1：安装助手</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-text-tertiary">
              请将下方的蓝色按钮，用鼠标 <b>拖拽</b> 到浏览器的 <b>书签收藏栏</b> 中。
            </p>
            <div className="flex justify-center p-6 border-2 border-dashed rounded-lg bg-surface-2">
              {/* 这是一个特殊的链接，拖动它就是添加书签 */}
              <a 
                href={bookmarkHref || '#'}
                aria-disabled={!bookmarkHref}
                className={`px-6 py-3 bg-accent text-on-accent font-bold rounded-pill shadow-card ${bookmarkHref ? 'hover:bg-accent-hover cursor-grab active:cursor-grabbing' : 'opacity-50 cursor-not-allowed'}`}
                onClick={(e) => e.preventDefault()} // 防止点击跳转
                title={bookmarkHref ? "拖动我到书签栏" : "正在生成书签…"}
              >
                GlobalPilot RPA
              </a>
            </div>
            <p className="text-sm text-text-secondary">
              注意：如果您的浏览器没有显示书签栏，请按 <kbd>Ctrl+Shift+B</kbd> (Windows) 或 <kbd>Cmd+Shift+B</kbd> (Mac) 打开。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>步骤 2：如何使用</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ol className="list-decimal list-inside space-y-2 text-text-tertiary">
              <li>在任务中心点击 <b>“一键发布”</b> 按钮。</li>
              <li>系统会自动并在新标签页打开 <b>小红书创作中心</b>。</li>
              <li>等待页面加载完毕（如有登录弹窗，请先登录）。</li>
              <li>点击浏览器书签栏上的 <b>GlobalPilot RPA</b>。</li>
              <li>见证奇迹：标题和正文会自动填充！</li>
            </ol>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 p-4 bg-warning/10 text-warning rounded-lg border border-warning">
        <h3 className="font-bold">为什么使用书签脚本？</h3>
        <p className="text-sm mt-1">
          由于浏览器安全限制，网页无法直接操作其他网站。书签脚本是最安全的“轻量级辅助”方案，
          <b>无需下载任何软件或插件</b>，完全利用浏览器原生功能，且不会被平台判定为外挂风险。
        </p>
      </div>
    </div>
  );
}
