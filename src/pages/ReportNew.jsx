import React, { useState } from 'react'
import ReportEditor from '../components/ReportEditor'
import DraftList from '../components/DraftList'

export default function ReportNew() {
  const [currentDraft, setCurrentDraft] = useState(null);
  const [refreshDrafts, setRefreshDrafts] = useState(0);
  const [editorKey, setEditorKey] = useState(0);

  const handleSaved = () => {
    setRefreshDrafts(prev => prev + 1);
  };

  const handleCreateNew = () => {
    setCurrentDraft(null);
    // 强制刷新编辑器组件
    setEditorKey(prev => prev + 1);
  };

  return (
    <div className="w-full h-[calc(100vh-64px)] bg-gray-50 rounded-xl overflow-hidden border border-gray-200 flex flex-col">
      <div className="p-8 overflow-y-auto flex-1">
        <div className="text-center mb-8 relative">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">新建报告</h2>
          <p className="text-gray-500">您可以在下方编写新的报告。</p>
          <p className="text-gray-500 mt-2 text-sm">如果您需要 AI 深度研究助手，请访问左侧的“报告生成助手”。</p>
          
          <button 
            onClick={handleCreateNew}
            className="absolute right-0 top-0 px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            重置 / 新建空白报告
          </button>
        </div>
        
        <div className="max-w-5xl mx-auto">
          <DraftList 
            onLoadDraft={setCurrentDraft} 
            refreshTrigger={refreshDrafts} 
          />
          
          <ReportEditor 
            key={editorKey}
            initialData={currentDraft} 
            onSaved={handleSaved}
            autoSaveInterval={30000}
          />
        </div>
      </div>
    </div>
  )
}
