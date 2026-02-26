import React, { useEffect, useState } from 'react';
import { reportService } from '../services/reportService';
import { FileText, Trash2, Edit } from 'lucide-react';

export default function DraftList({ onLoadDraft, refreshTrigger }) {
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(false);

  const [showAll, setShowAll] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const fetchDrafts = async () => {
    setLoading(true);
    try {
      const data = await reportService.getReports({ status: 'draft' });
      const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
      const sortedData = list.sort((a, b) => {
        const dateA = new Date(a?.updated_at || a?.created_at || 0);
        const dateB = new Date(b?.updated_at || b?.created_at || 0);
        return dateB - dateA;
      });
      setDrafts(sortedData);
    } catch (error) {
      console.error('Failed to fetch drafts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrafts();
  }, [refreshTrigger]);

  const handleDeleteClick = (e, id, title) => {
    e.stopPropagation();
    setPendingDelete({ id, title });
  };

  const performDelete = async (id) => {
    try {
      await reportService.deleteReport(id);
      fetchDrafts();
      setPendingDelete(null);
    } catch (error) {
      console.error('Failed to delete draft:', error);
      alert('删除失败');
    }
  };

  if (loading && drafts.length === 0) {
    return <div className="text-gray-500 text-sm mt-4">加载草稿中...</div>;
  }

  if (drafts.length === 0) {
    return null;
  }

  const visibleDrafts = showAll ? drafts : drafts.slice(0, 3);

  return (
    <div className="mt-8 mb-6">
      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setPendingDelete(null)}
        >
          <div
            className="w-[360px] rounded-lg border border-gray-200 bg-white p-5 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className="text-base font-medium text-gray-900">确认删除</h4>
            <p className="mt-2 text-sm text-gray-600">
              确定删除草稿「{pendingDelete.title || '无标题报告'}」吗？此操作不可恢复。
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="px-3 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={() => performDelete(pendingDelete.id)}
                className="px-3 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700"
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          草稿箱 ({drafts.length})
        </h3>
        {drafts.length > 3 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {showAll ? '收起' : '查看全部'}
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {visibleDrafts.map((draft) => (
          <div 
            key={draft.id} 
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white cursor-pointer group"
            onClick={() => onLoadDraft(draft)}
          >
            <div className="flex justify-between items-start">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {draft.title || '无标题报告'}
                </h4>
                <p className="text-xs text-gray-500 mt-1">
                  上次更新: {new Date(draft.updated_at || draft.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={(e) => handleDeleteClick(e, draft.id, draft.title || '无标题报告')}
                className="ml-2 text-gray-400 hover:text-red-500 transition-all"
                title="删除草稿"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-3 flex justify-end">
              <span className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center">
                <Edit className="w-3 h-3 mr-1" />
                继续编辑
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
