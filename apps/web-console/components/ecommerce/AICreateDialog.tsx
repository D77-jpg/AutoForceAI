"use client";
import React, { useState } from 'react';
import { 
    X, 
    Upload, 
    Sparkles, 
    Loader2, 
    ArrowRight,
    Wand2,
    CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface AIResult {
    name: string;
    subtitle: string;
    description: string;
    price: string;
    stock: string;
    categoryId: string; // ID mapping
    specs: Record<string, string>;
    images: string[];
}

interface AICreateDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (data: AIResult) => void;
}

export function AICreateDialog({ isOpen, onClose, onSuccess }: AICreateDialogProps) {
    const [step, setStep] = useState<'input' | 'processing' | 'result'>('input');
    const [prompt, setPrompt] = useState('');
    const [analyzingText, setAnalyzingText] = useState('');
    
    // Mock Result State
    const [result, setResult] = useState<AIResult | null>(null);

    if (!isOpen) return null;

    const handleGenerate = async () => {
        if (!prompt) return;
        
        setStep('processing');
        const steps = [
            "正在解析需求 (Analyzing Request)...",
            "生成商品图片 (Generating Images)...",
            "提取视觉特征 (Extracting Features)...",
            "撰写营销文案 (Writing Copy)...",
            "规划规格属性 (Defining Specs)..."
        ];

        for (const s of steps) {
            setAnalyzingText(s);
            await new Promise(r => setTimeout(r, 800));
        }

        // Mock Logic based on prompt: Expanded to be less "hardcoded" feeling
        const keywords = {
            dress: ['裙', 'dress', 'laced'],
            shirt: ['衬衫', 'shirt', 'blouse'],
            pants: ['裤', 'pants', 'jeans', 'trousers'],
            shoes: ['鞋', 'shoes', 'sneakers'],
            tech: ['手机', 'phone', '电脑', 'computer', 'tech']
        };

        const getType = (text: string) => {
            const lower = text.toLowerCase();
            if (keywords.dress.some(k => lower.includes(k))) return 'dress';
            if (keywords.shirt.some(k => lower.includes(k))) return 'shirt';
            if (keywords.pants.some(k => lower.includes(k))) return 'pants';
            if (keywords.shoes.some(k => lower.includes(k))) return 'shoes';
            if (keywords.tech.some(k => lower.includes(k))) return 'tech';
            return 'other';
        };

        const type = getType(prompt);
        const randomID = Math.floor(Math.random() * 1000) + 100;
        
        let mockData: AIResult;

        // Helper to generate dynamic description based on prompt
        const generateDesc = (template: string) => {
            return template.replace('PROMPT', prompt);
        };

        switch(type) {
            case 'dress':
                 mockData = {
                    name: `AI定制：${prompt.slice(0, 10)}... 时尚连衣裙`,
                    subtitle: "浪漫花卉 / 收腰显瘦 / 气质通勤",
                    categoryId: '11',
                    price: "299.00",
                    stock: "500",
                    description: `
**商品详情**
这款连衣裙采用高品质面料制作，触感柔软舒适。
- 立体剪裁
- 适合度假
- 设计灵感：${prompt}
                    `.trim(),
                    specs: { '颜色': '红色', '尺码': 'M', '材质': '雪纺' },
                    images: ["https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&fit=crop", "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=600&fit=crop"]
                };
                break;
            case 'shirt':
                mockData = {
                    name: `AI定制：${prompt.slice(0, 10)}... 商务衬衫`,
                    subtitle: "免烫抗皱 / 舒适透气 / 职场首选",
                    categoryId: '122',
                    price: "159.00",
                    stock: "800",
                    description: `
**商品详情**
商务人士首选，舒适透气。
* 适合场合：商务会议、日常通勤
* 设计重点：${prompt}
                    `.trim(),
                    specs: { '颜色': '白色', '尺码': 'L', '材质': '棉' },
                    images: ["https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&fit=crop"]
                };
                break;
            case 'pants':
                 mockData = {
                    name: `AI定制：${prompt.slice(0, 10)}... 潮流裤装`,
                    subtitle: "水洗做旧 / 显瘦版型 / 街头潮流",
                    categoryId: '22',
                    price: "189.00",
                    stock: "300",
                    description: `
**商品详情**
重磅丹宁面料，耐磨舒适。
- 风格：美式复古
- 细节：${prompt}
                    `.trim(),
                    specs: { '颜色': '牛仔蓝', '尺码': '30', '裤型': '直筒' },
                    images: ["https://images.unsplash.com/photo-1542272617-08f08630252c?w=600&fit=crop"]
                };
                break;
            default:
                 mockData = {
                    name: `AI智能生成: ${prompt.slice(0, 15)}...`,
                    subtitle: "品质保证 / 极速发货 / 售后无忧",
                    categoryId: '99',
                    price: (Math.random() * 500 + 50).toFixed(2),
                    stock: "100",
                    description: `
**商品详情**
根据您的描述生成的通用商品模板。
> ${prompt}

**产品特点**
- 智能匹配
- 高性价比
                    `.trim(),
                    specs: { '类型': '通用', '规格': '标准' },
                    images: ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&fit=crop"]
                };
        }

        setResult(mockData);
        setStep('result');
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg/60 backdrop-blur-sm">
            <div className="bg-surface border border-separator w-full max-w-lg rounded-xl shadow-modal overflow-hidden animate-modal-in">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-separator bg-surface/70">
                    <div className="flex items-center gap-2 text-accent">
                        <Sparkles size={20} />
                        <h3 className="font-bold text-lg text-text">AI 智能一键发布</h3>
                    </div>
                    <button onClick={onClose} className="text-text-secondary hover:text-text">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    {step === 'input' && (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-text">请输入商品描述或关键词</label>
                                <textarea 
                                    className="w-full h-32 bg-bg border border-separator rounded-lg p-3 text-text focus:ring-2 focus:ring-accent/40 focus:border-accent transition-all resize-none placeholder:text-text-tertiary"
                                    placeholder="例如：一件红色的法式复古碎花连衣裙，适合夏天海边度假，材质要轻薄透气..."
                                    value={prompt}
                                    onChange={e => setPrompt(e.target.value)}
                                />
                            </div>
                            
                            <div className="bg-warning/10 rounded-lg p-4 border border-warning/30 border-dashed">
                                <p className="text-xs text-warning/80 mb-3 text-center">或者上传参考图（可选）</p>
                                <div className="flex justify-center">
                                    <Button variant="outline" size="sm" className="bg-warning/10 border-warning/30 text-warning hover:bg-warning/20 hover:text-warning">
                                        <Upload size={14} className="mr-2" /> 上传图片
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 'processing' && (
                        <div className="py-10 flex flex-col items-center justify-center text-center space-y-4">
                            <div className="relative">
                                <div className="absolute inset-0 bg-accent blur-xl opacity-20 rounded-full animate-pulse"></div>
                                <Loader2 size={48} className="text-accent animate-spin relative z-10" />
                            </div>
                            <p className="text-text font-medium animate-pulse">{analyzingText}</p>
                        </div>
                    )}

                    {step === 'result' && result && (
                        <div className="space-y-4">
                            <div className="flex items-start gap-4 p-3 bg-surface/70 rounded-lg border border-separator">
                                <img src={result.images[0]} alt="Preview" className="w-16 h-16 rounded object-cover bg-surface-2" />
                                <div>
                                    <h4 className="text-sm font-bold text-text line-clamp-1">{result.name}</h4>
                                    <p className="text-xs text-text-secondary mt-1 line-clamp-2">{result.subtitle}</p>
                                    <div className="flex gap-2 mt-2">
                                        <span className="text-xs bg-accent/10 text-accent px-1.5 py-0.5 rounded">¥{result.price}</span>
                                        <span className="text-xs bg-surface-2 text-text px-1.5 py-0.5 rounded">ID: {result.categoryId}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-xs text-center text-success flex items-center justify-center gap-1">
                                <CheckCircle2 size={14} />
                                已生成完整商品信息，点击应用即可填充
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-surface/50 border-t border-separator flex justify-end gap-3">
                    {step === 'input' && (
                        <>
                            <Button variant="ghost" onClick={onClose} className="text-text-secondary hover:text-text">取消</Button>
                            <Button 
                                onClick={handleGenerate} 
                                className="bg-accent hover:bg-accent-hover text-white"
                                disabled={!prompt.trim()}
                            >
                                <Wand2 size={16} className="mr-2" />
                                开始生成
                            </Button>
                        </>
                    )}
                    
                    {step === 'result' && (
                        <>
                            <Button variant="ghost" onClick={() => setStep('input')} className="text-text-secondary hover:text-text">重试</Button>
                            <Button onClick={() => onSuccess(result!)} className="bg-success hover:bg-success text-white">
                                应用到表单
                                <ArrowRight size={16} className="ml-2" />
                            </Button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
