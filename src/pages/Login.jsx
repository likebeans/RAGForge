import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Lock, Key, Eye, EyeOff, FlaskConical, Loader2 } from 'lucide-react'
import { backendClient } from '../services/backend'
import { authService } from '../services/auth'

export default function Login() {
  const navigate = useNavigate()
  const [loginType, setLoginType] = useState('account')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    rememberMe: false
  })

  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate('/dashboard')
    }
  }, [navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await backendClient.login(formData.username, formData.password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-gray-50/50">
      {/* 左侧品牌区域 - 科技感/企业级风格优化 */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-slate-900 items-center justify-center">
        {/* 背景纹理 - 点阵网格 */}
        <div className="absolute inset-0 opacity-10" 
             style={{ 
               backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', 
               backgroundSize: '40px 40px' 
             }}>
        </div>
        
        {/* 氛围光效 - 增强空间层次 */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[128px]"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-[128px]"></div>
        </div>

        {/* 装饰性线条 - 数据流隐喻 */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,black,transparent)]"></div>

        {/* 内容容器 */}
        <div className="relative z-10 text-center px-12 max-w-2xl">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl shadow-2xl shadow-blue-500/30 mb-8 border border-white/10 backdrop-blur-xl group hover:scale-105 transition-transform duration-500">
            <FlaskConical className="w-12 h-12 text-white drop-shadow-md" />
          </div>
          
          <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">R&D AI Studio</h1>
          <p className="text-lg text-slate-300 font-light mb-12 max-w-md mx-auto leading-relaxed">
            新一代企业级研发智能化平台<br/>
            <span className="text-slate-400 text-base">让数据资产与人工智能深度融合，加速科研创新</span>
          </p>

          {/* 底部特性标签 */}
          <div className="flex items-center justify-center gap-6 text-sm font-medium text-slate-400/80">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/5 backdrop-blur-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"></div>
              Data Intelligence
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/5 backdrop-blur-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.6)]"></div>
              Smart Research
            </div>
          </div>
        </div>
      </div>

      {/* 右侧登录表单 - 视觉微调 */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 lg:p-16 bg-white">
        <div className="w-full max-w-[420px]">
          <div className="bg-white p-2">
            <div className="mb-10 text-center lg:text-left">
              <h2 className="text-3xl font-bold text-slate-900 mb-3 tracking-tight">
                欢迎回来
              </h2>
              <p className="text-slate-500 text-base">
                请登录您的账户以访问研发数据中心
              </p>
            </div>

            {/* 登录类型切换 - 优化样式 */}
            <div className="flex mb-8 bg-slate-100 p-1.5 rounded-xl">
              <button
                type="button"
                onClick={() => setLoginType('account')}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${
                  loginType === 'account'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                账号密码登录
              </button>
              <button
                type="button"
                onClick={() => setLoginType('sso')}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${
                  loginType === 'sso'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                SSO 登录
              </button>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
                <div className="text-red-500 mt-0.5">⚠️</div>
                <div className="text-red-600 text-sm font-medium">{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 用户名 */}
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">
                  用户名 / 企业邮箱
                </label>
                <div className="relative group">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
                  <input
                    type="text"
                    placeholder="请输入用户名"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* 密码 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-semibold text-slate-700">
                    密码
                  </label>
                  <a href="#" className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline">
                    忘记密码？
                  </a>
                </div>
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="请输入密码"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full pl-12 pr-12 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* 记住我 */}
              <div className="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  checked={formData.rememberMe}
                  onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"
                  disabled={loading}
                />
                <label htmlFor="remember-me" className="ml-2.5 block text-sm font-medium text-slate-600 cursor-pointer select-none">
                  记住我的登录状态
                </label>
              </div>

              {/* 登录按钮 */}
              <button
                type="submit"
                disabled={loading || !formData.username || !formData.password}
                className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.98] transition-all disabled:opacity-70 disabled:cursor-not-allowed disabled:shadow-none flex items-center justify-center gap-2"
              >
                {loading && <Loader2 className="w-5 h-5 animate-spin" />}
                {loading ? '正在验证...' : '登 录'}
              </button>

              {/* 底部信息 */}
              <div className="pt-6 mt-6 border-t border-slate-100 text-center">
                <p className="text-xs text-slate-400">
                  测试账号: <span className="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">admin</span> / <span className="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">admin123</span>
                </p>
                <p className="text-[10px] text-slate-300 mt-2">
                  Protected by Enterprise Security System. 
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
