import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { backendClient } from '../services/backend';
import ReportEditorComponent from '../components/ReportEditor';
import DraftList from '../components/DraftList';
import { ArrowLeft } from 'lucide-react';

export default function ReportEditor() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState(null);
  const [loading, setLoading] = useState(!!reportId);
  const [currentDraft, setCurrentDraft] = useState(null);
  const [refreshDrafts, setRefreshDrafts] = useState(0);
  const [editorKey, setEditorKey] = useState(0);

  // 如果是编辑模式，获取报告详情
  useEffect(() => {
    if (reportId) {
      fetchReport();
    }
  }, [reportId]);

  const fetchReport = async () => {
    try {
      const data = await backendClient.request('GET', `/api/reports/${reportId}`);
      setInitialData(data);
    } catch (error) {
      console.error('Failed to fetch report:', error);
      alert('加载报告失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSaved = (savedReport) => {
    setRefreshDrafts(prev => prev + 1);
    // 如果是新建保存成功，跳转到编辑页（或者保持在当前页但更新URL？）
    // 为了简单起见，这里我们保持在当前页，或者如果后端返回了ID且当前是新建，可以 navigate
    if (!reportId && savedReport && savedReport.id) {
       // navigate(`/reports/${savedReport.id}/edit`, { replace: true });
       // 但这样会导致重新加载。
       // 暂时不做跳转，只是刷新草稿箱
    }
  };

  const handleCreateNew = () => {
    if (reportId) {
        navigate('/reports/new');
    } else {
        setCurrentDraft(null);
        setInitialData(null);
        setRefreshDrafts(prev => prev + 1);
        setEditorKey(prev => prev + 1);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">加载中...</div>;

  return (
    <div className="w-full bg-gray-50 flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-white flex justify-between items-center">
        <button 
            onClick={() => navigate('/reports')}
            className="flex items-center text-gray-600 hover:text-gray-900"
        >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回列表
        </button>
        <h1 className="text-lg font-semibold text-gray-800">
            {reportId ? '编辑报告' : '新建报告'}
        </h1>
        <div className="w-20"></div> {/* Spacer */}
      </div>

      <div className="p-8">
        <div className="max-w-5xl mx-auto">
          {/* 只有在新建模式下才显示草稿箱 */}
          {!reportId && (
            <div className="mb-8 relative">
                <DraftList 
                    onLoadDraft={setCurrentDraft} 
                    refreshTrigger={refreshDrafts} 
                />
                 <button 
                    onClick={handleCreateNew}
                    className="absolute right-0 top-0 px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
                    style={{ marginTop: '-40px' }} // Adjust position
                  >
                    重置 / 新建空白报告
                  </button>
            </div>
          )}

          <ReportEditorComponent 
            key={editorKey}
            initialData={reportId ? initialData : currentDraft} 
            onSaved={handleSaved}
            autoSaveInterval={30000}
          />
        </div>
      </div>
    </div>
  );
}
