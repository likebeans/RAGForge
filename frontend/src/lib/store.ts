/**
 * 全局状态管理
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createClient, APIClient, KnowledgeBase, Conversation, ModelListResponse, ProviderConfig } from "./api";

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8020";

interface ProviderRuntimeConfig {
  apiKey?: string;
  baseUrl?: string;
  models?: Partial<ModelListResponse>;
  validated?: boolean;
  validatedAt?: string;
}

interface ProviderModelChoice {
  provider: string;
  model: string;
}

interface DefaultModelState {
  llm?: ProviderModelChoice;
  embedding?: ProviderModelChoice;
  rerank?: ProviderModelChoice;
}

interface AppState {
  // 配置
  apiKey: string;
  apiBase: string;
  providerCatalog: Record<string, ProviderConfig>;
  providerConfigs: Record<string, ProviderRuntimeConfig>;
  defaultModels: DefaultModelState;
  
  // 客户端
  client: APIClient | null;
  
  // 状态
  isConnected: boolean;
  knowledgeBases: KnowledgeBase[];
  selectedKbId: string | null;
  selectedKbIds: string[];
  
  // 对话管理
  conversations: Conversation[];
  currentConversationId: string | null;
  
  // Actions
  setApiKey: (key: string) => void;
  setApiBase: (base: string) => void;
  setProviderCatalog: (providers: Record<string, ProviderConfig>) => void;
  upsertProviderConfig: (provider: string, config: ProviderRuntimeConfig) => void;
  clearProviderConfig: (provider: string) => void;
  setDefaultModel: (type: keyof DefaultModelState, choice: ProviderModelChoice | null) => void;
  initClient: () => void;
  setConnected: (connected: boolean) => void;
  setKnowledgeBases: (kbs: KnowledgeBase[]) => void;
  selectKnowledgeBase: (id: string | null) => void;
  selectKnowledgeBases: (ids: string[]) => void;
  refreshKnowledgeBases: () => Promise<void>;
  
  // 对话 Actions
  setConversations: (conversations: Conversation[]) => void;
  setCurrentConversationId: (id: string | null) => void;
  refreshConversations: () => Promise<void>;
  createNewConversation: (title?: string, kbIds?: string[]) => Promise<string | null>;
  deleteConversation: (id: string) => Promise<void>;
  
  // 断开连接
  disconnect: () => void;
  
  // 自动重连（页面加载时调用）
  autoConnect: () => Promise<void>;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      apiKey: "",
      apiBase: DEFAULT_API_BASE,
      providerCatalog: {},
      providerConfigs: {},
      defaultModels: {},
      client: null,
      isConnected: false,
      knowledgeBases: [],
      selectedKbId: null,
      selectedKbIds: [],
      conversations: [],
      currentConversationId: null,

      setApiKey: (key) => {
        set({ apiKey: key });
        get().initClient();
      },

      setApiBase: (base) => {
        set({ apiBase: base });
        get().initClient();
      },

      initClient: () => {
        const { apiKey, apiBase } = get();
        if (apiKey) {
          const client = createClient(apiKey, apiBase);
          set({ client });
        } else {
          set({ client: null });
        }
      },

      setConnected: (connected) => set({ isConnected: connected }),

      setKnowledgeBases: (kbs) => set({ knowledgeBases: kbs }),

      setProviderCatalog: (providers) => set({ providerCatalog: providers }),

      upsertProviderConfig: (provider, config) =>
        set((state) => ({
          providerConfigs: {
            ...state.providerConfigs,
            [provider]: {
              ...state.providerConfigs[provider],
              ...config,
            },
          },
        })),

      clearProviderConfig: (provider) =>
        set((state) => {
          const next = { ...state.providerConfigs };
          delete next[provider];
          return { providerConfigs: next };
        }),

      setDefaultModel: (type, choice) =>
        set((state) => ({
          defaultModels: {
            ...state.defaultModels,
            [type]: choice || undefined,
          },
        })),

      selectKnowledgeBase: (id) =>
        set({
          selectedKbId: id,
          selectedKbIds: id ? [id] : [],
        }),

      selectKnowledgeBases: (ids) =>
        set({
          selectedKbIds: ids,
          selectedKbId: ids[0] || null,
        }),

      refreshKnowledgeBases: async () => {
        const { client } = get();
        if (!client) return;
        try {
          const result = await client.listKnowledgeBases();
          set({ knowledgeBases: result.items });
        } catch (error) {
          console.error("Failed to refresh knowledge bases:", error);
        }
      },

      // 对话管理方法
      setConversations: (conversations) => set({ conversations }),

      setCurrentConversationId: (id) => set({ currentConversationId: id }),

      refreshConversations: async () => {
        const { client } = get();
        if (!client) return;
        try {
          const result = await client.listConversations();
          set({ conversations: result.items });
        } catch (error) {
          console.error("Failed to refresh conversations:", error);
        }
      },

      createNewConversation: async (title, kbIds) => {
        const { client } = get();
        if (!client) return null;
        try {
          const conversation = await client.createConversation(title, kbIds);
          await get().refreshConversations();
          set({ currentConversationId: conversation.id });
          return conversation.id;
        } catch (error) {
          console.error("Failed to create conversation:", error);
          return null;
        }
      },

      deleteConversation: async (id) => {
        const { client } = get();
        if (!client) return;
        try {
          await client.deleteConversation(id);
          const { currentConversationId } = get();
          if (currentConversationId === id) {
            set({ currentConversationId: null });
          }
          await get().refreshConversations();
        } catch (error) {
          console.error("Failed to delete conversation:", error);
        }
      },

      disconnect: () => {
        set({
          apiKey: "",
          client: null,
          isConnected: false,
          knowledgeBases: [],
          selectedKbId: null,
          conversations: [],
          currentConversationId: null,
        });
      },

      // 自动重连：页面加载时如果有保存的 apiKey，自动测试连接
      autoConnect: async () => {
        const { apiKey, apiBase, client, isConnected } = get();
        
        // 如果已经连接，跳过
        if (isConnected && client) return;
        
        // 如果没有 apiKey，跳过
        if (!apiKey) return;
        
        // 创建客户端
        const newClient = createClient(apiKey, apiBase);
        set({ client: newClient });
        
        // 带重试的健康检查（解决后端连接池冷启动问题）
        const healthCheckWithRetry = async (maxRetries = 2, delay = 500): Promise<boolean> => {
          for (let i = 0; i <= maxRetries; i++) {
            try {
              await newClient.health();
              return true;
            } catch {
              if (i < maxRetries) {
                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, delay));
              }
            }
          }
          return false;
        };
        
        // 测试连接（使用健康检查接口，带重试）
        const connected = await healthCheckWithRetry();
        if (connected) {
          set({ isConnected: true });
          
          // 加载知识库列表
          try {
            const result = await newClient.listKnowledgeBases();
            set({ knowledgeBases: result.items });
          } catch {
            // 忽略知识库加载失败
          }
          
          // 加载对话列表
          try {
            const convResult = await newClient.listConversations();
            set({ conversations: convResult.items });
          } catch {
            // 忽略对话加载失败
          }
        } else {
          // 连接失败，保持断开状态
          set({ isConnected: false });
        }
      },
    }),
    {
      name: "rag-app-storage",
      partialize: (state) => ({
        apiKey: state.apiKey,
        apiBase: state.apiBase,
        selectedKbId: state.selectedKbId,
        selectedKbIds: state.selectedKbIds,
        providerCatalog: state.providerCatalog,
        providerConfigs: state.providerConfigs,
        defaultModels: state.defaultModels,
      }),
    }
  )
);
