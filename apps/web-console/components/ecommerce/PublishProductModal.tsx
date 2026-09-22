"use client";
import React, { useState, useEffect } from 'react';
import { 
    X, 
    CheckCircle2, 
    Sparkles, 
    Loader2, 
    Globe, 
    ShoppingCart, 
    ExternalLink,
    AlertCircle
} from 'lucide-react';

interface PublishModalProps {
    isOpen: boolean;
    onClose: () => void;
    product: any | null; // Pass the product to publish
    onConfirm: (productId: number, platforms: string[]) => void;
}

export function PublishProductModal({ isOpen, onClose, product, onConfirm }: PublishModalProps) {
    const [step, setStep] = useState<'check' | 'select' | 'publishing' | 'success'>('check');
    const [checks, setChecks] = useState({
        compliance: 'pending', // pending, loading, success, error
        seo: 'pending',
        image: 'pending',
        price: 'pending'
    });
    const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['official']);

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setStep('check');
            setChecks({ compliance: 'pending', seo: 'pending', image: 'pending', price: 'pending' });
            runAiChecks();
        }
    }, [isOpen]);

    const runAiChecks = async () => {
        // Step 1: Compliance
        setChecks(prev => ({ ...prev, compliance: 'loading' }));
        await new Promise(r => setTimeout(r, 600));
        setChecks(prev => ({ ...prev, compliance: 'success' }));

        // Step 2: SEO
        setChecks(prev => ({ ...prev, seo: 'loading' }));
        await new Promise(r => setTimeout(r, 800));
         setChecks(prev => ({ ...prev, seo: 'success' }));

        // Step 3: Image
        setChecks(prev => ({ ...prev, image: 'loading' }));
        await new Promise(r => setTimeout(r, 500));
        setChecks(prev => ({ ...prev, image: 'success' }));

         // Step 4: Price
         setChecks(prev => ({ ...prev, price: 'loading' }));
         await new Promise(r => setTimeout(r, 400));
         setChecks(prev => ({ ...prev, price: 'success' }));

         // Done
         setTimeout(() => setStep('select'), 500);
    };

    const handlePublish = async () => {
        setStep('publishing');
        await new Promise(r => setTimeout(r, 1500)); // Mock API call
        
        onConfirm(product?.id, selectedPlatforms);
        setStep('success');
    };

    if (!isOpen || !product) return null;

    const togglePlatform = (id: string) => {
        if (selectedPlatforms.includes(id)) {
            setSelectedPlatforms(selectedPlatforms.filter(p => p !== id));
        } else {
            setSelectedPlatforms([...selectedPlatforms, id]);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-[#1c1c1e] border border-white/10 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* Header */}
                <div className="p-5 border-b border-white/5 flex justify-between items-center bg-white/5">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Sparkles className="text-[#0a84ff]" size={18} />
                        AI 智能发布发布中心
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto">
                    
                    {/* Step 1: AI Safety Checks */}
                    {(step === 'check' || step === 'select' || step === 'publishing') && (
                        <div className="mb-8">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">1. AI 预检 (Pre-flight Checks)</h4>
                            <div className="space-y-3">
                                <CheckItem label="合规性检测 (Compliance Check)" status={checks.compliance} />
                                <CheckItem label="SEO 关键词优化 (Keyword Optimization)" status={checks.seo} />
                                <CheckItem label="视觉质量评估 (Visual QA)" status={checks.image} />
                                <CheckItem label="竞品价格核查 (Pricing Strategy)" status={checks.price} />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Channel Selection */}
                    {(step === 'select' || step === 'publishing') && (
                        <div className="transition-opacity duration-500 opacity-100">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">2. 选择发布渠道 (Distribution Channels)</h4>
                            <div className="grid grid-cols-1 gap-3">
                                <PlatformOption 
                                    id="official" 
                                    name="官方商城 (Official Store)" 
                                    icon={<Globe size={16} />} 
                                    selected={selectedPlatforms.includes('official')}
                                    onClick={() => togglePlatform('official')}
                                />
                                <PlatformOption 
                                    id="tiktok" 
                                    name="TikTok Shop (Douyin)" 
                                    icon={<span className="font-bold text-xs">Tik</span>} 
                                    selected={selectedPlatforms.includes('tiktok')}
                                    onClick={() => togglePlatform('tiktok')}
                                />
                                <PlatformOption 
                                    id="amazon" 
                                    name="Amazon Store" 
                                    icon={<ShoppingCart size={16} />} 
                                    selected={selectedPlatforms.includes('amazon')}
                                    onClick={() => togglePlatform('amazon')}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 3: Success */}
                    {step === 'success' && (
                        <div className="text-center py-8">
                            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle2 className="text-green-500" size={32} />
                            </div>
                            <h4 className="text-xl font-bold text-white mb-2">发布成功！</h4>
                            <p className="text-slate-400 text-sm mb-6">
                                商品 "{product.name}" 已成功推送至 {selectedPlatforms.length} 个渠道。
                            </p>
                            <div className="flex justify-center gap-3">
                                <button className="px-4 py-2 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-white/5" onClick={onClose}>
                                    返回列表
                                </button>
                                <a href="http://127.0.0.1:3002" target="_blank" className="px-4 py-2.5 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-full text-sm font-medium flex items-center gap-2">
                                    <ExternalLink size={14} /> 去商城查看
                                </a>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {step !== 'success' && (
                    <div className="p-5 border-t border-white/5 bg-black/20 flex justify-end gap-3 rounded-b-2xl">
                        <button 
                            onClick={onClose}
                            className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            取消
                        </button>
                        <button 
                            disabled={step !== 'select' || selectedPlatforms.length === 0}
                            onClick={handlePublish}
                            className="px-6 py-2.5 bg-[#0071e3] hover:bg-[#0077ed] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-full text-sm font-medium shadow-apple transition-all flex items-center gap-2"
                        >
                            {step === 'publishing' && <Loader2 className="animate-spin" size={16} />}
                            {step === 'publishing' ? '正在发布...' : '确认发布 (Publish)'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

function CheckItem({ label, status }: { label: string, status: string }) {
    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
            <span className="text-sm text-slate-300">{label}</span>
            <div className="flex items-center gap-2">
                {status === 'pending' && <span className="text-xs text-slate-500">等待中...</span>}
                {status === 'loading' && <Loader2 className="animate-spin text-[#0a84ff]" size={16} />}
                {status === 'success' && <CheckCircle2 className="text-green-500" size={18} />}
                {status === 'error' && <AlertCircle className="text-red-500" size={18} />}
            </div>
        </div>
    );
}

function PlatformOption({ id, name, icon, selected, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${selected ? 'bg-[#0a84ff]/10 border-[#0a84ff]/40' : 'bg-transparent border-white/10 hover:border-white/20'}`}
        >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${selected ? 'bg-[#0a84ff] text-white' : 'bg-white/10 text-slate-400'}`}>
                {icon}
            </div>
            <span className={`text-sm font-medium ${selected ? 'text-white' : 'text-slate-400'}`}>{name}</span>
            {selected && <CheckCircle2 className="ml-auto text-[#0a84ff]" size={16} />}
        </button>
    );
}
