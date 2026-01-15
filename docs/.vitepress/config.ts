import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Self-RAG Pipeline',
  description: '多租户知识库检索服务 - Multi-tenant Knowledge Base Retrieval Service',
  lang: 'zh-CN',
  
  // 基础配置
  base: '/',
  cleanUrls: true,
  
  // 主题配置
  themeConfig: {
    // 网站标题和 Logo
    siteTitle: 'Self-RAG Pipeline',
    
    // 导航菜单
    nav: [
      { text: '首页', link: '/' },
      { text: '入门指南', link: '/getting-started/' },
      { text: '开发文档', link: '/development/' },
      { text: '系统架构', link: '/architecture/' },
      { text: '运维部署', link: '/operations/' },
      { text: '参考资料', link: '/reference/' }
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
      
      '/development/': [
        {
          text: '开发文档',
          items: [
            { text: '概述', link: '/development/' },
            { text: '贡献指南', link: '/development/contributing' },
            { text: '测试指南', link: '/development/testing' },
            { text: '管道开发', link: '/development/pipeline-development' },
            { text: '多租户开发', link: '/development/multi-tenant-development' },
            { text: '问题排查', link: '/development/troubleshooting' }
          ]
        }
      ],
      
      '/architecture/': [
        {
          text: '系统架构',
          items: [
            { text: '概述', link: '/architecture/' },
            { text: '系统设计', link: '/architecture/system-design' },
            { text: 'API 规范', link: '/architecture/api-specification' },
            { text: '管道架构', link: '/architecture/pipeline-architecture' },
            { text: '架构决策', link: '/architecture/decisions' }
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
            { text: '监控指南', link: '/operations/monitoring' },
            { text: '问题排查', link: '/operations/troubleshooting' }
          ]
        }
      ],
      
      '/reference/': [
        {
          text: '参考资料',
          items: [
            { text: '概述', link: '/reference/' },
            { text: '变更日志', link: '/reference/changelog' },
            {
              text: '中文内容',
              collapsed: false,
              items: [
                { text: '中文内容索引', link: '/reference/chinese/' },
                { text: '开发指南', link: '/reference/chinese/development-guide' },
                { text: '优化指南', link: '/reference/chinese/optimization-guide' },
                { text: '实践总结', link: '/reference/chinese/practice-summary' }
              ]
            },
            {
              text: '历史文档',
              collapsed: true,
              items: [
                { text: '历史索引', link: '/reference/history/' },
                { text: '第一阶段开发', link: '/reference/history/phase1-development' },
                { text: '第二阶段开发', link: '/reference/history/phase2-development' },
                { text: '第三阶段测试', link: '/reference/history/phase3-development' }
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
    // Vite 配置选项
  }
})