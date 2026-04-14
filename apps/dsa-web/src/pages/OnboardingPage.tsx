import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from 'motion/react';
import { Cpu, TrendingUp, Network, ArrowRight, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, ParticleBackground } from '../components/common';
import { StepLLMSetup, StepAddStocks, StepFirstAnalysis } from '../components/onboarding';
import { onboardingApi } from '../api/onboarding';
import type { OnboardingStatus } from '../api/onboarding';
import { useAuth } from '../hooks';
import { cn } from '../utils/cn';

const STEPS = [
  { label: 'AI 配置', key: 'llmConfigured' as const },
  { label: '添加股票', key: 'stocksAdded' as const },
  { label: '首次分析', key: 'firstAnalysisDone' as const },
];

const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const { setOnboardingCompleted } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [, setStatus] = useState<OnboardingStatus | null>(null);
  const [stepCompleted, setStepCompleted] = useState([false, false, false]);
  const [addedStocks, setAddedStocks] = useState<{ stockCode: string; stockName: string }[]>([]);

  useEffect(() => {
    document.title = '引导设置 - DSA';
  }, []);

  // Parallax mouse tracking (same as Login/Register)
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const smoothX = useSpring(mouseX, { damping: 30, stiffness: 200 });
  const smoothY = useSpring(mouseY, { damping: 30, stiffness: 200 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = e.clientX / window.innerWidth - 0.5;
      const y = e.clientY / window.innerHeight - 0.5;
      mouseX.set(x);
      mouseY.set(y);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  // Fetch onboarding status and skip completed steps
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const s = await onboardingApi.getStatus();
        setStatus(s);
        if (s.completed) {
          navigate('/', { replace: true });
          return;
        }
        // Mark completed steps
        const completed = [
          s.steps.llmConfigured,
          s.steps.stocksAdded,
          s.steps.firstAnalysisDone,
        ];
        setStepCompleted(completed);
        // Skip to first incomplete step
        const firstIncomplete = completed.findIndex((c) => !c);
        if (firstIncomplete >= 0) {
          setCurrentStep(firstIncomplete);
        }
      } catch {
        // If fetch fails, start from step 0
      }
    };
    void fetchStatus();
  }, [navigate]);

  const handleComplete = useCallback(async () => {
    try {
      await onboardingApi.complete();
      setOnboardingCompleted(true);
    } catch {
      // Best-effort
    }
    navigate('/', { replace: true });
  }, [navigate, setOnboardingCompleted]);

  const handleSkip = useCallback(() => {
    void handleComplete();
  }, [handleComplete]);

  const handleStepComplete = useCallback(
    (stepIndex: number) => {
      setStepCompleted((prev) => {
        const next = [...prev];
        next[stepIndex] = true;
        return next;
      });
      // Auto-advance to next step
      if (stepIndex < 2) {
        setCurrentStep(stepIndex + 1);
      }
    },
    []
  );

  const handleNext = useCallback(() => {
    if (currentStep < 2) {
      setCurrentStep(currentStep + 1);
    } else {
      void handleComplete();
    }
  }, [currentStep, handleComplete]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep]);

  return (
    <div className="relative flex min-h-screen flex-col justify-center overflow-hidden bg-[var(--login-bg-main)] py-6 font-sans selection:bg-[var(--login-accent-soft)] sm:py-12 sm:px-6 lg:px-8 [perspective:1500px]">
      {/* Dynamic Background */}
      <ParticleBackground />

      {/* Cyber Grid */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,var(--login-grid-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--login-grid-line)_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:var(--login-grid-mask)]" />

      {/* Parallax Glowing Orbs */}
      <motion.div
        style={{
          x: useTransform(smoothX, [-0.5, 0.5], [-50, 50]),
          y: useTransform(smoothY, [-0.5, 0.5], [-50, 50]),
        }}
        className="absolute left-[20%] top-[20%] -z-10 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--login-accent-glow)] blur-[100px]"
      />
      <motion.div
        style={{
          x: useTransform(smoothX, [-0.5, 0.5], [60, -60]),
          y: useTransform(smoothY, [-0.5, 0.5], [60, -60]),
        }}
        className="absolute right-[20%] bottom-[10%] -z-10 h-[400px] w-[400px] translate-x-1/2 translate-y-1/2 rounded-full bg-emerald-600/10 blur-[120px]"
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-lg relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="flex flex-col items-center justify-center mb-8 relative"
        >
          <motion.div
            style={{
              x: useTransform(smoothX, [-0.5, 0.5], [-8, 8]),
              y: useTransform(smoothY, [-0.5, 0.5], [-8, 8]),
              rotate: useTransform(smoothX, [-0.5, 0.5], [-0.5, 0.5]),
            }}
            className="pointer-events-none absolute -top-[20vh] -z-10 opacity-80"
          >
            <div className="relative flex h-[120vh] w-[120vh] items-center justify-center rounded-full border border-[var(--login-accent-soft)] bg-gradient-to-br from-[var(--login-accent-soft)] to-[hsl(214_100%_20%_/_0.18)] shadow-[inset_0_0_200px_var(--login-accent-glow)] blur-[4px]">
              <Cpu className="h-[70vh] w-[70vh] text-[hsl(200_80%_22%_/_0.4)] brightness-50" />
              <TrendingUp className="absolute h-[25vh] w-[25vh] translate-x-[15vh] translate-y-[15vh] text-emerald-900/30 brightness-50" />
            </div>
          </motion.div>

          <div className="mt-8 flex flex-col items-center">
            <h2 className="text-3xl font-extrabold tracking-tighter text-[var(--login-text-primary)] sm:text-4xl">
              <span className="bg-gradient-to-r from-[var(--login-text-primary)] via-[var(--login-text-primary)] to-[var(--login-text-secondary)] bg-clip-text text-transparent">
                欢迎使用{' '}
              </span>
              <span className="bg-gradient-to-r from-[var(--login-brand-start)] to-[var(--login-brand-end)] bg-clip-text text-transparent drop-shadow-[0_0_20px_var(--login-accent-glow)]">
                DSA
              </span>
            </h2>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-4 flex items-center gap-2 rounded-full border border-[var(--login-accent-border)] bg-[var(--login-accent-soft)] px-3 py-1 text-[10px] font-medium text-[var(--login-accent-text)] backdrop-blur-sm"
          >
            <Network className="h-3 w-3" />
            <span>SETUP WIZARD</span>
          </motion.div>
        </motion.div>

        {/* Stepper */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mb-6 flex items-center justify-center gap-0"
        >
          {STEPS.map((step, i) => (
            <div key={step.key} className="flex items-center">
              <button
                type="button"
                onClick={() => setCurrentStep(i)}
                className="flex flex-col items-center gap-1"
              >
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-all duration-300',
                    i < currentStep || stepCompleted[i]
                      ? 'border-emerald-400 bg-emerald-400/20 text-emerald-400'
                      : i === currentStep
                        ? 'border-[var(--login-accent-text)] bg-[var(--login-accent-soft)] text-[var(--login-accent-text)] shadow-[0_0_12px_var(--login-accent-glow)]'
                        : 'border-[var(--login-border-card)] bg-transparent text-[var(--login-text-muted)]'
                  )}
                >
                  {i < currentStep || stepCompleted[i] ? (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={cn(
                    'text-[10px] font-medium',
                    i === currentStep
                      ? 'text-[var(--login-accent-text)]'
                      : 'text-[var(--login-text-muted)]'
                  )}
                >
                  {step.label}
                </span>
              </button>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'mx-2 mt-[-16px] h-0.5 w-12 rounded-full transition-colors duration-300',
                    i < currentStep || stepCompleted[i]
                      ? 'bg-emerald-400/40'
                      : 'bg-[var(--login-border-card)]'
                  )}
                />
              )}
            </div>
          ))}
        </motion.div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative group z-20 pointer-events-auto"
        >
          {/* Card Border Glow */}
          <div className="pointer-events-none absolute -inset-0.5 rounded-3xl bg-gradient-to-b from-[var(--login-accent-glow)] to-[hsl(214_100%_56%_/_0.18)] opacity-50 blur-sm transition duration-1000 group-hover:opacity-100 group-hover:duration-200" />

          <div className="pointer-events-auto relative flex flex-col overflow-hidden rounded-3xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/80 p-4 shadow-2xl backdrop-blur-xl sm:p-8">
            {/* Inner corner glow */}
            <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-[var(--login-accent-soft)] blur-[50px]" />
            <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-blue-600/10 blur-[50px]" />

            {/* Step content */}
            <div className="relative z-10 min-h-[240px] sm:min-h-[320px]">
              {currentStep === 0 && (
                <StepLLMSetup onComplete={() => handleStepComplete(0)} />
              )}
              {currentStep === 1 && (
                <StepAddStocks
                  onComplete={() => handleStepComplete(1)}
                  addedStocks={addedStocks}
                  setAddedStocks={setAddedStocks}
                />
              )}
              {currentStep === 2 && (
                <StepFirstAnalysis
                  onComplete={() => void handleComplete()}
                  addedStocks={addedStocks}
                />
              )}
            </div>

            {/* Footer navigation */}
            <div className="relative z-10 mt-8 flex items-center justify-between border-t border-[var(--login-border-card)] pt-6">
              <div className="flex items-center gap-3">
                {currentStep > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleBack}
                    className="text-[var(--login-text-muted)] hover:text-[var(--login-text-secondary)]"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    上一步
                  </Button>
                )}
                <button
                  type="button"
                  onClick={handleSkip}
                  className="text-sm text-[var(--login-text-muted)] transition-colors hover:text-[var(--login-text-secondary)] hover:underline"
                >
                  跳过引导
                </button>
              </div>

              {currentStep < 2 && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleNext}
                  className="bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] text-[var(--login-button-text)]"
                >
                  下一步
                  <ArrowRight className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Footer info */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center font-mono text-xs uppercase tracking-wider text-[var(--login-text-muted)]"
        >
          Step {currentStep + 1} of {STEPS.length} — Onboarding Wizard
        </motion.p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
      `}} />
    </div>
  );
};

export default OnboardingPage;
