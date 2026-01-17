# PRD: Meowart Frontend Authentication System

## 概述

基于后端 API (`https://api.meowart.ai`) 开发前端 Web 应用的认证系统。前端需要实现完整的用户认证流程，包括 Google OAuth 登录、邮箱密码注册/登录、会话管理和用户状态检测。

## 架构

| 组件 | 域名 | 说明 |
|------|------|------|
| Frontend | `https://meowart.ai` | React/Next.js Web App |
| Backend | `https://api.meowart.ai` | FastAPI Server |

> [!IMPORTANT]
> **跨域 Cookie**: 后端设置的 Cookie 使用 `domain=".meowart.ai"`，前端和后端共享同一个 Session Cookie。所有 API 请求必须带上 `credentials: 'include'`。

---

## API 端点

### 认证 API 列表

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/auth/google/login` | 跳转 Google OAuth 登录 | - | 302 重定向到 Google |
| GET | `/api/auth/google/callback` | Google OAuth 回调 | - | 302 重定向到前端 |
| **POST** | **`/api/auth/send-code`** | **发送邮箱验证码** | `{email}` | `SendCodeResponse` |
| POST | `/api/auth/register` | 邮箱注册 (需验证码) | `{email, password, code}` | `AuthResponse` |
| POST | `/api/auth/login` | 邮箱登录 | `{email, password}` | `AuthResponse` |
| GET | `/api/auth/me` | 获取当前用户 | - | `UserProfile` |
| POST | `/api/auth/logout` | 登出 | - | `AuthResponse` |

### 数据模型

```typescript
// 发送验证码请求
interface SendCodeRequest {
  email: string;      // 有效的邮箱格式
}

// 发送验证码响应
interface SendCodeResponse {
  message: string;    // "验证码已发送，请查收邮箱"
}

// 用户注册请求 (需要验证码)
interface UserCreate {
  email: string;      // 有效的邮箱格式
  password: string;   // 最少 8 位
  code: string;       // 6 位数字验证码
}

// 用户登录请求
interface UserLogin {
  email: string;
  password: string;
}

// 用户资料 (GET /api/auth/me 响应)
interface UserProfile {
  id: number;
  email: string;
  avatar_url: string | null;  // Google 用户会有头像
}

// 认证响应 (register/login/logout 响应)
interface AuthResponse {
  message: string;
  user?: UserProfile;
}

// 错误响应
interface ErrorResponse {
  detail: string;
}
```

---

## 用户故事 & 功能需求

### FE-001: 登录页面 (`/login`)

**描述**: 用户访问登录页面，可以选择 Google 登录或邮箱密码登录。

**UI 要求**:
- [ ] 显示 **"Sign in with Google"** 按钮
- [ ] 显示邮箱输入框
- [ ] 显示密码输入框
- [ ] 显示 **"登录"** 按钮
- [ ] 显示 **"还没有账户？立即注册"** 链接，跳转到 `/register`
- [ ] 登录成功后跳转到首页 `/`

**交互逻辑**:

```
┌─────────────────────────────────────────────────────────┐
│  点击 "Sign in with Google"                              │
│    └──> window.location.href = API_URL + "/api/auth/google/login"
│    └──> 后端处理 OAuth 后自动重定向回前端首页              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  点击 "登录" (邮箱密码)                                   │
│    └──> POST /api/auth/login {email, password}           │
│    └──> 成功: 跳转首页，显示用户信息                       │
│    └──> 失败 (401): 显示错误 "邮箱或密码错误"              │
└─────────────────────────────────────────────────────────┘
```

**验证规则**:
- 邮箱: 必填，有效邮箱格式
- 密码: 必填

---

### FE-002: 注册页面 (`/register`)

**描述**: 用户使用邮箱验证码 + 密码创建新账户。

**UI 要求**:
- [ ] 显示邮箱输入框
- [ ] 显示 **"发送验证码"** 按钮 (邮箱输入框右侧)
- [ ] 显示验证码输入框 (6位数字)
- [ ] 显示密码输入框 (带密码强度提示)
- [ ] 显示确认密码输入框
- [ ] 显示 **"注册"** 按钮
- [ ] 显示 **"已有账户？立即登录"** 链接
- [ ] 显示 **"或使用 Google 注册"** 按钮
- [ ] 注册成功后自动登录并跳转首页

**交互逻辑**:

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 发送验证码                                       │
│    └──> 输入邮箱，点击 "发送验证码"                         │
│    └──> POST /api/auth/send-code {email}                 │
│    └──> 成功: 显示 "验证码已发送"，按钮变为 60 秒倒计时      │
│    └──> 失败 (429): 显示 "请求太频繁，请稍后再试"           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Step 2: 完成注册                                         │
│    └──> 输入验证码、密码、确认密码                          │
│    └──> 前端校验: 密码 >= 8 位，两次密码一致                │
│    └──> POST /api/auth/register {email, password, code}  │
│    └──> 成功 (201): 自动登录，跳转首页                      │
│    └──> 失败 (400): 显示 "验证码错误或已过期"               │
│    └──> 失败 (400): 显示 "该邮箱已被注册"                   │
└─────────────────────────────────────────────────────────┘
```

**「发送验证码」按钮状态**:

| 状态 | 显示文本 | 是否可点击 |
|------|----------|------------|
| 初始 | 发送验证码 | ✅ (邮箱有效时) |
| 发送中 | 发送中... | ❌ |
| 倒计时 | 60s 后重试 | ❌ |
| 倒计时结束 | 重新发送 | ✅ |

**验证规则**:
- 邮箱: 必填，有效邮箱格式
- 验证码: 必填，6 位数字
- 密码: 必填，最少 8 位
- 确认密码: 必须与密码一致

**参考代码**:

```typescript
// 发送验证码
const [countdown, setCountdown] = useState(0);
const [sending, setSending] = useState(false);

const handleSendCode = async () => {
  if (!email || countdown > 0) return;
  
  setSending(true);
  try {
    const res = await api.post('/api/auth/send-code', { email });
    if (res.ok) {
      setCountdown(60);  // 开始 60 秒倒计时
      toast.success('验证码已发送，请查收邮箱');
    } else if (res.status === 429) {
      toast.error('请求太频繁，请稍后再试');
    }
  } finally {
    setSending(false);
  }
};

// 倒计时 Hook
useEffect(() => {
  if (countdown > 0) {
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }
}, [countdown]);

// 注册
const handleRegister = async () => {
  const res = await api.post('/api/auth/register', { email, password, code });
  if (res.ok) {
    const data = await res.json();
    setUser(data.user);
    router.push('/');
  } else {
    const error = await res.json();
    toast.error(error.detail);  // "验证码错误或已过期" 或 "该邮箱已被注册"
  }
};
```

---

### FE-003: 会话检测 (全局状态)

**描述**: 应用启动时自动检测用户登录状态，并维护全局用户状态。

**实现要求**:
- [ ] App 初始化时调用 `GET /api/auth/me`
- [ ] 如果返回 `UserProfile` → 用户已登录
- [ ] 如果返回 401 → 用户未登录
- [ ] 使用 Context/Store 管理全局用户状态

**参考代码**:

```typescript
// hooks/useAuth.ts
const useAuth = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/auth/me`, {
      credentials: 'include',  // 必须！发送 Cookie
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => setUser(data))
      .finally(() => setLoading(false));
  }, []);

  return { user, loading, setUser };
};
```

---

### FE-004: 导航栏用户状态

**描述**: 根据用户登录状态显示不同的导航栏内容。

**UI 要求**:

**未登录状态**:
- [ ] 显示 **"登录"** 按钮
- [ ] 显示 **"注册"** 按钮

**已登录状态**:
- [ ] 显示用户头像 (如果有 `avatar_url`)
- [ ] 显示用户邮箱或下拉菜单
- [ ] 显示 **"退出登录"** 按钮/选项

---

### FE-005: 退出登录

**描述**: 用户点击退出登录后，清除登录状态。

**交互逻辑**:
```
点击 "退出登录"
  └──> POST /api/auth/logout (credentials: 'include')
  └──> 清除本地用户状态
  └──> 跳转到首页或登录页
```

---

### FE-006: 受保护路由

**描述**: 某些页面需要登录后才能访问。

**实现要求**:
- [ ] 创建 `ProtectedRoute` 组件
- [ ] 未登录用户访问受保护页面时，重定向到 `/login`
- [ ] 登录后自动跳回原页面 (保存 redirect URL)

**参考实现**:

```typescript
// components/ProtectedRoute.tsx
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push(`/login?redirect=${encodeURIComponent(window.location.pathname)}`);
    }
  }, [user, loading]);

  if (loading) return <LoadingSpinner />;
  if (!user) return null;
  return children;
};
```

---

## 技术要求

### API 调用配置

> [!CAUTION]
> 所有 API 请求**必须**包含 `credentials: 'include'`，否则 Cookie 不会被发送/接收！

```typescript
// lib/api.ts
const API_URL = 'https://api.meowart.ai';

export const api = {
  get: (path: string) => 
    fetch(`${API_URL}${path}`, {
      credentials: 'include',
    }),
  
  post: (path: string, body: object) =>
    fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    }),
};
```

### 环境变量

```env
NEXT_PUBLIC_API_URL=https://api.meowart.ai
```

---

## 页面路由

| 路径 | 组件 | 说明 | 访问权限 |
|------|------|------|----------|
| `/` | HomePage | 首页 | 公开 |
| `/login` | LoginPage | 登录页 | 公开 (已登录则跳转首页) |
| `/register` | RegisterPage | 注册页 | 公开 (已登录则跳转首页) |
| `/profile` | ProfilePage | 用户资料 | 需登录 |

---

## 错误处理

| HTTP 状态码 | 场景 | 前端处理 |
|-------------|------|----------|
| 400 | 邮箱已注册 | 显示 "该邮箱已被注册" |
| 400 | 验证码错误/过期 | 显示 "验证码错误或已过期" |
| 401 | 登录失败 / 未认证 | 显示 "邮箱或密码错误" 或跳转登录页 |
| 429 | 验证码发送太频繁 | 显示 "请求太频繁，请稍后再试" |
| 500 | 服务器错误 | 显示 "服务器错误，请稍后重试" |

---

## 测试清单

- [ ] Google 登录流程完整 (点击 → 授权 → 回调 → 显示用户信息)
- [ ] 发送验证码成功，60秒内无法重复发送
- [ ] 使用正确验证码完成邮箱注册
- [ ] 使用错误/过期验证码注册失败并显示错误
- [ ] 邮箱登录成功
- [ ] 重复注册相同邮箱显示错误
- [ ] 错误密码登录显示错误
- [ ] 刷新页面后保持登录状态
- [ ] 退出登录后用户状态清除
- [ ] 受保护页面未登录时跳转登录页
- [ ] 跨域 Cookie 正常工作

---

## 设计参考

建议参考现代登录页面设计:
- 简洁的卡片式布局
- Google 登录按钮使用官方样式
- 表单验证使用实时反馈
- 加载状态使用骨架屏或 Spinner
- 错误提示使用 Toast 或内联样式
