import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Check, ExternalLink, Loader2, Sparkles, Bot, Star, Zap } from 'lucide-react';
import { Button, Input } from '../common';
import { systemConfigApi } from '../../api/systemConfig';
import { cn } from '../../utils/cn';

type Provider = {
  id: string;
  name: string;
  subtitle: string;
  icon: React.ReactNode;
  configKeys: { key: string; value: string }[];
  apiKeyField: string;
  link: string;
  protocol: string;
  baseUrl?: string;
  models: string[];
};

const PROVIDERS: Provider[] = [
  {
    id: 'gemini',
    name: 'Gemini',
    subtitle: '免费可用',
    icon: <Sparkles className="h-5 w-5" />,
    configKeys: [],
    apiKeyField: 'GEMINI_API_KEY',
    link: 'https://aistudio.google.com/',
    protocol: 'gemini',
    models: ['gemini-2.0-flash'],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    subtitle: '高性价比',
    icon: <Zap className="h-5 w-5" />,
    configKeys: [
      { key: 'OPENAI_BASE_URL', value: 'https://api.deepseek.com/v1' },
      { key: 'OPENAI_MODEL', value: 'deepseek-chat' },
    ],
    apiKeyField: 'OPENAI_API_KEY',
    link: 'https://platform.deepseek.com/',
    protocol: 'openai',
    baseUrl: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat'],
  },
  {
    id: 'openai',
    name: 'OpenAI',
    subtitle: 'GPT 系列',
    icon: <Bot className="h-5 w-5" />,
    configKeys: [],
    apiKeyField: 'OPENAI_API_KEY',
    link: 'https://platform.openai.com/',
    protocol: 'openai',
    models: ['gpt-4o-mini'],
  },
  {
    id: 'aihubmix',
    name: 'AIHubMix',
    subtitle: '一Key全能',
    icon: <Star className="h-5 w-5" />,
    configKeys: [],
    apiKeyField: 'AIHUBMIX_KEY',
    link: 'https://aihubmix.com/',
    protocol: 'openai',
    baseUrl: 'https://aihubmix.com/v1',
    models: ['gpt-4o-mini'],
  },
];

interface StepLLMSetupProps {
  onComplete: () => void;
}

export function StepLLMSetup({ onComplete }: StepLLMSetupProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const selected = PROVIDERS.find((p) => p.id === selectedId) ?? null;

  const handleTest = async () => {
    if (!selected || !apiKey.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await systemConfigApi.testLLMChannel({
        name: 'onboarding-test',
        protocol: selected.protocol,
        baseUrl: selected.baseUrl ?? '',
        apiKey: apiKey.trim(),
        models: selected.models,
        enabled: true,
        timeoutSeconds: 20,
      });
      setTestResult({ success: result.success, message: result.message });
    } catch {
      setTestResult({ success: false, message: '连接测试失败，请检查 API Key' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!selected || !apiKey.trim()) return;
    setSaving(true);
    try {
      // First get current config version
      const config = await systemConfigApi.getConfig(false);
      const items = [
        { key: selected.apiKeyField, value: apiKey.trim() },
        ...selected.configKeys,
      ];
      await systemConfigApi.update({
        configVersion: config.configVersion,
        items,
      });
      onComplete();
    } catch {
      setTestResult({ success: false, message: '保存配置失败，请重试' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-[var(--login-text-primary)]">
          配置 AI 模型
        </h3>
        <p className="mt-1 text-sm text-[var(--login-text-secondary)]">
          选择一个 AI 服务商，填入 API Key 即可开始分析
        </p>
      </div>

      {/* Provider cards */}
      <div className="grid grid-cols-2 gap-3">
        {PROVIDERS.map((provider) => (
          <button
            key={provider.id}
            type="button"
            onClick={() => {
              setSelectedId(provider.id);
              setApiKey('');
              setTestResult(null);
            }}
            className={cn(
              'relative flex flex-col items-center gap-2 rounded-2xl border p-4 transition-all duration-200',
              'hover:border-[var(--login-accent-border)] hover:bg-[var(--login-accent-soft)]',
              selectedId === provider.id
                ? 'border-[var(--login-accent-border)] bg-[var(--login-accent-soft)] shadow-[0_0_20px_var(--login-accent-glow)]'
                : 'border-[var(--login-border-card)] bg-transparent'
            )}
          >
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                selectedId === provider.id
                  ? 'bg-[var(--login-accent-glow)] text-[var(--login-accent-text)]'
                  : 'bg-[var(--login-accent-soft)] text-[var(--login-text-secondary)]'
              )}
            >
              {provider.icon}
            </div>
            <span className="text-sm font-medium text-[var(--login-text-primary)]">
              {provider.name}
            </span>
            <span className="text-xs text-[var(--login-text-muted)]">
              {provider.subtitle}
            </span>
            {selectedId === provider.id && (
              <motion.div
                layoutId="provider-check"
                className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white"
              >
                <Check className="h-3 w-3" />
              </motion.div>
            )}
          </button>
        ))}
      </div>

      {/* API Key input */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-4 rounded-2xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/40 p-4">
              <Input
                label="API Key"
                type="password"
                appearance="login"
                allowTogglePassword
                iconType="key"
                placeholder={`输入 ${selected.name} API Key`}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setTestResult(null);
                }}
              />

              <div className="flex items-center justify-between gap-3">
                <a
                  href={selected.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-[var(--login-accent-text)] hover:underline"
                >
                  获取 Key
                  <ExternalLink className="h-3 w-3" />
                </a>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTest}
                    disabled={!apiKey.trim() || testing}
                    isLoading={testing}
                    loadingText="测试中..."
                    className="border-[var(--login-accent-border)] text-[var(--login-accent-text)] hover:bg-[var(--login-accent-soft)]"
                  >
                    测试连接
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleSave}
                    disabled={!apiKey.trim() || !testResult?.success || saving}
                    isLoading={saving}
                    loadingText="保存中..."
                    className="bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] text-[var(--login-button-text)]"
                  >
                    <Check className="h-4 w-4" />
                    保存
                  </Button>
                </div>
              </div>

              {/* Test result */}
              <AnimatePresence>
                {testResult && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className={cn(
                      'flex items-center gap-2 rounded-xl px-3 py-2 text-sm',
                      testResult.success
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    )}
                  >
                    {testResult.success ? (
                      <Check className="h-4 w-4 shrink-0" />
                    ) : (
                      <Loader2 className="h-4 w-4 shrink-0" />
                    )}
                    {testResult.message}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
