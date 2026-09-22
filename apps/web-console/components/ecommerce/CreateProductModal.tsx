"use client";
import React, { useState, useRef } from 'react';
import { 
    X, 
    Upload, 
    Sparkles, 
    Loader2, 
    CheckCircle2, 
    Image as ImageIcon,
    Type,
    Tag,
    DollarSign,
    Box,
    Wand2,
    ArrowRight
} from 'lucide-react';

interface CreateProductModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (newProduct: any) => void;
    initialData?: any; // Add for Edit Mode
}

export function CreateProductModal({ isOpen, onClose, onSuccess, initialData }: CreateProductModalProps) {
    const [step, setStep] = useState<'source' | 'analyzing' | 'review'>('source');
    const [activeTab, setActiveTab] = useState<'upload' | 'generate'>('generate'); // Default to AI
    const [analyzingStep, setAnalyzingStep] = useState<string>('');
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    
    // AI Generate State
    const [genPrompt, setGenPrompt] = useState("French vintage floral dress, chiffon, v-neck, summer vibe, high quality photography");
    const [isImageGenerating, setIsImageGenerating] = useState(false);
    
    // Form Data (AI Generated)
    const [formData, setFormData] = useState({
        name: "",
        category: "",
        price: "",
        description: "",
        attributes: {} as any,
        tags: [] as string[]
    });

    // Detect Edit Mode
    React.useEffect(() => {
        if (isOpen && initialData) {
            setStep('review');
            setPreviewImage(initialData.images?.[0] || null);
            setFormData({
                name: initialData.name,
                category: initialData.category || "Uncategorized",
                price: String(initialData.price),
                description: initialData.description || "",
                attributes: initialData.attributes || {},
                tags: initialData.tags || []
            });
        }
    }, [isOpen, initialData]);

    // Mock Analysis Workflow
    const startAnalysis = async (imgUrl: string) => {
        setStep('analyzing');
        setPreviewImage(imgUrl);
        
        const steps = [
            "识别商品主体 (Detecting Object)...",
            "提取视觉特征 (Extracting Features: Color, Material, Style)...",
            "生成营销文案 (Generating Copywriting)...",
            "匹配价格策略 (Matching Pricing Strategy)...",
            "构建 SEO 标签 (Building SEO Tags)..."
        ];

        for (const s of steps) {
            setAnalyzingStep(s);
            await new Promise(r => setTimeout(r, 800));
        }

        // Mock Result for a Woman's Dress
        setFormData({
            name: "2026春夏新款法式复古收腰碎花连衣裙 (French Vintage Floral Dress)",
            category: "女装 / 连衣裙 / 碎花裙",
            price: "299.00",
            description: genPrompt.includes("dress") ? "这不仅仅是一条裙子，更是您夏日优雅的宣言。采用高透气雪纺面料，亲肤舒适；经典的V领设计修饰颈部线条，收腰剪裁完美展现身姿。适合约会、度假或下午茶时光。" : "AI 智能生成的商品描述...",
            attributes: {
                "材质": "雪纺 (Chiffon)",
                "风格": "复古 (Vintage)",
                "袖长": "短袖",
                "腰型": "高腰",
                "图案": "碎花"
            },
            tags: ["夏季穿搭", "法式复古", "显瘦", "温柔风"]
        });

        setStep('review');
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const url = URL.createObjectURL(e.target.files[0]);
            startAnalysis(url);
        }
    };
    
    const handleAiGenerate = async () => {
        setIsImageGenerating(true);
        try {
            const res = await fetch('http://127.0.0.1:8002/content/generate-image', {
                method: 'POST', 
                body: JSON.stringify({ prompt: genPrompt, resolution: "1024*1024" }),
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            
            if (data.success && data.url) {
                // Determine if we start analysis immediately or let user preview first.
                // Flow: User sees image -> Clicks "Use this Image" -> Analysis starts.
                // Since this is inside the "generate" tab, we just set the preview image here?
                // Actually, let's auto-start analysis to be seamless as requested: "自动完成相关信息的完善"
                // But usually generation takes time, user might want to see if it's good.
                // Let's settle on: Show result in tab, add "Next" button.
                setPreviewImage(data.url);
            } else {
                alert("Generation failed, using mock.");
                setPreviewImage("https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=2520&auto=format&fit=crop");
            }
        } catch (e) {
            console.error(e);
            setPreviewImage("https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=2520&auto=format&fit=crop");
        } finally {
            setIsImageGenerating(false);
        }
    };

    const handleCreate = async () => {
        const productPayload = {
            name: formData.name,
            sku_code: initialData ? initialData.sku_code : `SKU-${Math.floor(Math.random()*90000)+10000}`,
            price: Number(formData.price),
            stock_quantity: initialData ? initialData.stock_quantity : 100,
            attributes: formData.attributes,
            images: [previewImage || "/placeholder.jpg"],
            embedding_status: 'embedded',
            status: initialData ? initialData.status : 'draft',
            description: formData.description
        };

        try {
            let res;
            if (initialData) {
                // Update Mode
                res = await fetch(`http://127.0.0.1:8002/api/v1/products/${initialData.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productPayload)
                });
            } else {
                // Create Mode
                res = await fetch('http://127.0.0.1:8002/api/v1/products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productPayload)
                });
            }

            if (res.ok) {
                const savedProduct = await res.json();
                onSuccess(savedProduct);
                onClose();
                // Reset
                setTimeout(() => {
                    setStep('source');
                    setPreviewImage(null);
                    setAnalyzingStep('');
                    // Clear initialData related state if needed, though parent handles passing it
                }, 500);
            } else {
                alert("Failed to save product to database.");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving product.");
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className={`bg-[#1c1c1e] border border-white/10 w-full rounded-2xl shadow-2xl overflow-hidden flex flex-col transition-all duration-500 ${step === 'review' ? 'max-w-4xl h-[80vh]' : 'max-w-xl'}`}>
                
                {/* Header */}
                <div className="p-5 border-b border-white/5 flex justify-between items-center bg-white/5">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Wand2 className="text-[#0a84ff]" size={20} />
                        {initialData ? "编辑商品 (Edit Product)" : "AI 新品构建 (Product Creator)"}
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-0 flex-1 overflow-hidden flex flex-col relative">
                    
                    {/* Step 1: Source Selection (Generate or Upload) */}
                    {step === 'source' && (
                        <div className="flex flex-col h-full">
                            {/* Tabs */}
                            <div className="flex border-b border-white/5">
                                <button 
                                    onClick={() => setActiveTab('generate')}
                                    className={`flex-1 py-4 text-sm font-medium transition-colors ${activeTab === 'generate' ? 'text-[#0a84ff] border-b-2 border-[#0a84ff] bg-white/5' : 'text-slate-400 hover:text-white'}`}
                                >
                                    <Sparkles size={14} className="inline mr-2" />
                                    AI 生成 (Text-to-Product)
                                </button>
                                <button 
                                    onClick={() => setActiveTab('upload')}
                                    className={`flex-1 py-4 text-sm font-medium transition-colors ${activeTab === 'upload' ? 'text-[#0a84ff] border-b-2 border-[#0a84ff] bg-white/5' : 'text-slate-400 hover:text-white'}`}
                                >
                                    <Upload size={14} className="inline mr-2" />
                                    本地上传 (Upload Image)
                                </button>
                            </div>

                            {/* Tab Content */}
                            <div className="flex-1 p-8">
                                {activeTab === 'generate' ? (
                                    <div className="h-full flex flex-col gap-4">
                                        <div className="flex-1 min-h-0 flex flex-col items-center justify-center gap-4">
                                            {previewImage ? (
                                                 <div className="relative w-full h-64 rounded-xl overflow-hidden border border-white/10 group">
                                                    <img src={previewImage} className="w-full h-full object-contain bg-black/40" />
                                                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                                        <button onClick={() => setPreviewImage(null)} className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded text-xs backdrop-blur">
                                                            重试
                                                        </button>
                                                    </div>
                                                 </div>
                                            ) : isImageGenerating ? (
                                                <div className="text-center space-y-4">
                                                    <div className="w-16 h-16 bg-[#0a84ff]/10 rounded-full flex items-center justify-center mx-auto animate-pulse">
                                                        <Loader2 className="animate-spin text-[#0a84ff]" size={32} />
                                                    </div>
                                                    <p className="text-slate-400 text-sm">正在调用云端模型生成设计图...</p>
                                                </div>
                                            ) : (
                                                <div className="text-center text-slate-500 text-sm">
                                                    输入描述，AI 将为您创造独一无二的商品图片
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex flex-col gap-3">
                                            <textarea 
                                                value={genPrompt}
                                                onChange={(e) => setGenPrompt(e.target.value)}
                                                className="w-full h-24 bg-black/20 border border-white/10 rounded-xl p-3 text-sm text-slate-300 focus:border-[#0a84ff] outline-none resize-none"
                                                placeholder="Describe the product (e.g. Red silk evening gown...)"
                                            />
                                            <div className="flex justify-end gap-2">
                                                 {previewImage ? (
                                                     <button 
                                                        onClick={() => startAnalysis(previewImage)}
                                                        className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full text-sm font-medium shadow-lg transition-all flex items-center gap-2"
                                                     >
                                                         使用此图并分析 <ArrowRight size={16} />
                                                     </button>
                                                 ) : (
                                                     <button 
                                                        onClick={handleAiGenerate}
                                                        disabled={isImageGenerating || !genPrompt}
                                                        className="px-6 py-2.5 bg-[#0071e3] hover:bg-[#0077ed] disabled:opacity-50 text-white rounded-full text-sm font-medium shadow-lg transition-all flex items-center gap-2"
                                                     >
                                                         {isImageGenerating ? '生成中...' : '开始生成 (Generate)'}
                                                     </button>
                                                 )}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center space-y-6">
                                        <div className="text-center">
                                            <h4 className="text-lg font-bold text-white mb-2">拖拽或点击上传</h4>
                                            <p className="text-slate-400 text-xs">支持 JPG, PNG • 最大 10MB</p>
                                        </div>
                                        <label className="relative group cursor-pointer">
                                            <input type="file" className="hidden" accept="image/*" onChange={handleFileSelect} />
                                            <div className="flex items-center gap-3 px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-slate-300 rounded-xl font-medium transition-all">
                                                <Upload size={20} />
                                                选择本地图片
                                            </div>
                                        </label>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Analyzing */}
                    {step === 'analyzing' && (
                        <div className="p-10 flex flex-col items-center justify-center h-full space-y-8">
                             <div className="relative">
                                {/* Scanning Effect Overlay on Image */}
                                <div className="w-48 h-48 rounded-lg overflow-hidden relative border-2 border-[#0a84ff]/40 shadow-2xl">
                                    {previewImage && <img src={previewImage} className="w-full h-full object-cover opacity-50" />}
                                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0a84ff]/20 to-transparent w-full h-full animate-scan"></div>
                                </div>
                                <div className="absolute -bottom-3 -right-3 bg-[#0071e3] text-white text-[10px] px-2 py-1 rounded-full font-mono flex items-center gap-1">
                                    <Loader2 size={10} className="animate-spin" /> PROCESSING
                                </div>
                             </div>

                             <div className="text-center space-y-2">
                                 <h4 className="text-lg font-bold text-white">AI 数字导购正在分析...</h4>
                                 <p className="text-[#64d2ff] font-mono text-sm h-6 transition-all">{analyzingStep}</p>
                             </div>
                        </div>
                    )}

                    {/* Step 3: Review */}
                    {step === 'review' && (
                        <div className="flex h-full">
                            {/* Left: Image & Quick Stats */}
                            <div className="w-1/3 bg-black/20 p-6 border-r border-white/5 flex flex-col gap-4">
                                <div className="aspect-[3/4] bg-white/5 rounded-lg overflow-hidden border border-white/10 relative group">
                                    {previewImage && <img src={previewImage} className="w-full h-full object-cover" />}
                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                        <button className="px-4 py-2 bg-white/10 backdrop-blur text-white rounded-lg text-xs hover:bg-white/20">更换图片</button>
                                    </div>
                                </div>
                                
                                <div className="space-y-3">
                                    <h5 className="text-xs font-bold text-slate-500 uppercase">Detect Traits</h5>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(formData.attributes).map(([k,v]: any) => (
                                            <span key={k} className="px-2 py-1 bg-[#0a84ff]/10 text-[#64d2ff] border border-[#0a84ff]/20 rounded text-xs">
                                                {v}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Right: AI Generated Form */}
                            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                                <div className="space-y-6">
                                    <div className="flex items-center gap-2 mb-2 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-xs">
                                        <CheckCircle2 size={16} />
                                        <span>分析完成！AI 已自动为您填充 90% 的商品信息。</span>
                                    </div>

                                    {/* Title */}
                                    <div className="space-y-2">
                                        <label className="text-xs text-slate-400 uppercase font-bold flex items-center gap-1">
                                             <Type size={14} /> 商品标题 (Product Title)
                                        </label>
                                        <input 
                                            type="text" 
                                            value={formData.name}
                                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:border-[#0a84ff] focus:bg-white/10 transition-all outline-none font-medium"
                                        />
                                    </div>

                                    {/* Category & Price Grid */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-xs text-slate-400 uppercase font-bold flex items-center gap-1">
                                                <Tag size={14} /> 类目 (Category)
                                            </label>
                                            <input 
                                                type="text" 
                                                value={formData.category} 
                                                onChange={(e) => setFormData({...formData, category: e.target.value})}
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-slate-300 outline-none focus:border-[#0a84ff]"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-slate-400 uppercase font-bold flex items-center gap-1">
                                                <DollarSign size={14} /> 建议售价 (Price)
                                            </label>
                                            <div className="relative">
                                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">¥</span>
                                                <input 
                                                    type="text" 
                                                    value={formData.price} 
                                                    onChange={(e) => setFormData({...formData, price: e.target.value})}
                                                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-4 py-3 text-emerald-400 font-mono font-bold outline-none focus:border-[#0a84ff]"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Description */}
                                    <div className="space-y-2">
                                        <label className="text-xs text-slate-400 uppercase font-bold flex items-center justify-between">
                                            <span className="flex items-center gap-1"><Box size={14} /> AI 营销文案 (Description)</span>
                                            <button className="text-[10px] text-[#0a84ff] hover:text-white flex items-center gap-1">
                                                <Sparkles size={10} /> 重新生成
                                            </button>
                                        </label>
                                        <textarea 
                                            value={formData.description}
                                            onChange={(e) => setFormData({...formData, description: e.target.value})}
                                            className="w-full h-32 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-slate-300 leading-relaxed outline-none focus:border-[#0a84ff] resize-none"
                                        />
                                    </div>

                                    {/* Tags */}
                                    <div className="space-y-2">
                                        <label className="text-xs text-slate-400 uppercase font-bold">SEO Tags</label>
                                        <div className="flex flex-wrap gap-2">
                                            {formData.tags.map(tag => (
                                                <span key={tag} className="px-3 py-1 bg-white/5 hover:bg-white/10 rounded-full text-xs text-slate-300 border border-white/5 cursor-pointer transition-colors">
                                                    #{tag}
                                                </span>
                                            ))}
                                            <button className="px-3 py-1 border border-dashed border-white/20 rounded-full text-xs text-slate-500 hover:text-white hover:border-white/50">
                                                + Add
                                            </button>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                    )}

                </div>

                {/* Footer */}
                {step === 'review' && (
                    <div className="p-5 border-t border-white/5 bg-black/20 flex justify-end gap-3 rounded-b-2xl">
                        <button 
                            onClick={() => {
                                setStep('source');
                                setPreviewImage(null);
                                setAnalyzingStep('');
                                onClose();
                            }}
                            className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            放弃 (Discard)
                        </button>
                        <button 
                            onClick={handleCreate}
                            className="px-8 py-2 bg-[#0071e3] hover:bg-[#0077ed] text-white rounded-full text-sm font-medium shadow-apple transition-all flex items-center gap-2"
                        >
                            {initialData ? '保存修改 (Update)' : '确认创建商品 (Create)'} <ArrowRight size={16} />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

// Add some CSS for scanning animation in global css or inline here if needed
// For now, assuming standard tailwind setup. Adding style tag for animation.
const style = `
@keyframes scan {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}
.animate-scan {
    animation: scan 2s linear infinite;
}
`;
