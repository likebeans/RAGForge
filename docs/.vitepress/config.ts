import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Self-RAG Pipeline',
  description: '多租户知识库检索服务 - Multi-tenant Knowledge Base Retrieval Service',
  lang: 'zh-CN',
  
  // 基础配置
  base: '/',
  cleanUrls: true,
  ignoreDeadLinks: true,
  
  // 主题配置
  themeConfig: {
    // 网站标题和 Logo
    siteTitle: 'Self-RAG Pipeline',
    
    // 导航菜单
    nav: [
      { text: '首页', link: '/' },
      { text: '入门', link: '/getting-started/' },
      { text: '指南', link: '/guides/' },
      { text: '架构', link: '/architecture/' },
      { text: '开发', link: '/development/' },
      { text: '运维', link: '/operations/' },
      { text: '报告', link: '/reports/' }
    ],
    
    // 侧边栏配置
    sidebar: {
      '/getting-started/': [
        {
          text: '入门指南',
          items: [
            { text: '概述', link: '/getting-started/' },
            { text: '安装指南', link: '/getting-started/installation' },
            { text: '配置指南', link: '/getting-started/configuration' },
            { text: '快速开始', link: '/getting-started/quick-start' },
            { text: '第一个 API 调用', link: '/getting-started/first-api-call' }
          ]
        }
      ],

      '/guides/': [
        {
          text: '使用指南',
          items: [
            { text: '概述', link: '/guides/' },
            { text: '环境配置', link: '/guides/environment-config' },
            { text: '部署指南', link: '/guides/deployment' },
            { text: 'API 集成', link: '/guides/api-integration' },
            { text: '权限管理', link: '/guides/permissions' },
            { text: 'OpenAI SDK', link: '/guides/openai-sdk' },
            { text: 'Admin Token', link: '/guides/admin-token-guide' },
            { text: '生产清单', link: '/guides/production-checklist' },
            { text: '数据迁移', link: '/guides/migration-sparse-es' }
          ]
        }
      ],
      
      '/architecture/': [
        {
          text: '系统架构',
          items: [
            { text: '概览', link: '/architecture/overview' },
            { text: '系统设计', link: '/architecture/system-design' },
            { text: 'Pipeline 架构', link: '/architecture/pipeline-architecture' },
            { text: 'API 规范', link: '/architecture/api-specification' },
            { text: '架构决策', link: '/architecture/decisions' },
            { 
              text: '核心特性',
              items: [
                 { text: '富文本解析器', link: '/architecture/features/rich-text-parser' }
              ]
            },
            { text: '架构更新', link: '/architecture/architecture-updates' }
          ]
        }
      ],

      '/development/': [
        {
          text: '开发文档',
          items: [
            { text: '概述', link: '/development/' },
            { text: '贡献指南', link: '/development/contributing' },
            { text: '测试指南', link: '/development/testing' },
            { text: 'Pipeline 开发', link: '/development/pipeline-development' },
            { text: '多租户开发', link: '/development/multi-tenant-development' },
            { text: '问题排查', link: '/development/troubleshooting' }
          ]
        }
      ],
      
      '/operations/': [
        {
          text: '运维部署',
          items: [
            { text: '概述', link: '/operations/' },
            { text: '部署指南', link: '/operations/deployment' },
            { text: '安全指南', link: '/operations/security' },
            { text: '监控指南', link: '/operations/monitoring' }
          ]
        }
      ],

      '/reports/': [
        {
          text: '报告与历史',
          items: [
            { text: '概述', link: '/reports/' },
            { text: '项目评估', link: '/reports/assessment' },
            { text: '优化测试', link: '/reports/optimization-test-report' },
            { text: 'OpenAI SDK 测试', link: '/reports/openai-sdk-testing' },
            { text: '代码审查', link: '/reports/code-review-report' },
            { 
              text: '历史阶段',
              collapsed: false,
              items: [
                { text: 'Phase 1', link: '/reports/history/phase1' },
                { text: 'Phase 2', link: '/reports/history/phase2' },
                { text: 'Phase 3', link: '/reports/history/phase3' }
              ]
            }
          ]
        }
      ],
      
      '/reference/': [
        {
          text: '参考资料',
          items: [
            { text: '概述', link: '/reference/' },
            {
              text: '中文内容',
              collapsed: false,
              items: [
                { text: '索引', link: '/reference/chinese/' },
                { text: 'API 设计', link: '/reference/chinese/api-design' },
                { text: '开发指南', link: '/reference/chinese/development' },
                { text: '优化经验', link: '/reference/chinese/optimization' },
                { text: '实践总结', link: '/reference/chinese/practice-summary' },
                { text: '租户开发', link: '/reference/chinese/tenant-development' }
              ]
            }
          ]
        }
      ]
    },
    
    // 搜索配置
    search: {
      provider: 'local',
      options: {
        locales: {
          zh: {
            translations: {
              button: {
                buttonText: '搜索文档',
                buttonAriaLabel: '搜索文档'
              },
              modal: {
                noResultsText: '无法找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: {
                  selectText: '选择',
                  navigateText: '切换'
                }
              }
            }
          }
        }
      }
    },
    
    // 页脚配置
    footer: {
      message: 'Self-RAG Pipeline - 多租户知识库检索服务',
      copyright: 'Copyright © 2024'
    },
    
    // 编辑链接
    editLink: {
      pattern: 'https://github.com/your-org/self-rag-pipeline/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },
    
    // 最后更新时间
    lastUpdated: {
      text: '最后更新于',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium'
      }
    },
    
    // 社交链接
    socialLinks: [
      { icon: 'github', link: 'https://github.com/your-org/self-rag-pipeline' }
    ]
  },
  
  // Markdown 配置
  markdown: {
    lineNumbers: true,
    config: (md) => {
      // 可以在这里添加 markdown-it 插件
    }
  },
  
  // 构建配置
  vite: {
    build: {
      chunkSizeWarningLimit: 1600
    }
  }
})
