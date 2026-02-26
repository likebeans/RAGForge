import React, { useState, useEffect, useRef, useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import TurndownService from 'turndown';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { reportService } from '../services/reportService';

export default function ReportEditor({ initialData = null, onSaved, autoSaveInterval = 30000 }) {
  const [title, setTitle] = useState(initialData?.title || '');
  const [content, setContent] = useState(''); // Stores HTML for ReactQuill
  const [reportId, setReportId] = useState(initialData?.id || null);
  const [lastSaved, setLastSaved] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [quillKey, setQuillKey] = useState(0); // Key to force re-render ReactQuill
  
  const autoSaveTimerRef = useRef(null);
  const lastContentRef = useRef(''); // Stores HTML
  const lastTitleRef = useRef(title);
  const isMountedRef = useRef(true);
  const prevInitialIdRef = useRef(initialData?.id || null);
  
  // Turndown service for HTML -> Markdown
  const turndownService = useMemo(() => {
    const service = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced',
      emDelimiter: '*'
    });
    return service;
  }, []);

  marked.setOptions({ gfm: true, breaks: true });

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, []);

  // Initial Data Loading - only react when initialData.id actually changes
  useEffect(() => {
    if (!isMountedRef.current) return;
    const newId = initialData?.id || null;
    const prevId = prevInitialIdRef.current;
    // Only when ID changes do we remount the editor content
    if (newId !== prevId) {
      prevInitialIdRef.current = newId;
      if (initialData) {
        setTitle(initialData.title || '');
        setReportId(initialData.id);
        const html = DOMPurify.sanitize(marked.parse(initialData.content || ''));
        setContent(html);
        setQuillKey(prev => prev + 1);
        lastContentRef.current = html;
        lastTitleRef.current = initialData.title || '';
      } else {
        // Parent会在“重置”时通过外层key销毁重建本组件，因此这里不再额外清空，避免无意重置
        setTitle('');
        setReportId(null);
        setContent('');
        setQuillKey(prev => prev + 1);
        lastContentRef.current = '';
        lastTitleRef.current = '';
        setLastSaved(null);
      }
    }
  }, [initialData]);

  const saveReport = async (status = 'draft') => {
    if (!isMountedRef.current) return;
    
    setIsSaving(true);
    try {
      // Convert HTML back to Markdown for storage
      const markdownContent = turndownService.turndown(content);
      const data = { title, content: markdownContent, status };
      
      let result;
      if (reportId) {
        result = await reportService.updateReport(reportId, data);
      } else {
        result = await reportService.createReport(data);
        if (isMountedRef.current) {
          setReportId(result.id);
        }
      }
      
      if (isMountedRef.current) {
        setLastSaved(new Date());
        lastContentRef.current = content;
        lastTitleRef.current = title;
        if (onSaved) onSaved(result);
      }
      return result;
    } catch (error) {
      console.error('Failed to save report:', error);
      if (isMountedRef.current) {
        alert('保存失败: ' + error.message);
      }
    } finally {
      if (isMountedRef.current) {
        setIsSaving(false);
      }
    }
  };

  useEffect(() => {
    const checkAndSave = async () => {
      if (!isMountedRef.current) return;
      
      // Compare HTML content changes
      if (
        (content !== lastContentRef.current || title !== lastTitleRef.current) &&
        (title || content)
      ) {
        await saveReport('draft');
      }
    };

    autoSaveTimerRef.current = setInterval(checkAndSave, autoSaveInterval);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, [content, title, reportId, autoSaveInterval]);

  const modules = useMemo(() => ({
    toolbar: [
      [{ 'header': [1, 2, 3, false] }],
      ['bold', 'italic', 'underline', 'strike', 'blockquote'],
      [{'list': 'ordered'}, {'list': 'bullet'}],
      ['link', 'image', 'code-block'],
      ['clean']
    ],
  }), []);

  const formats = useMemo(() => [
    'header',
    'bold', 'italic', 'underline', 'strike', 'blockquote',
    'list', 'bullet',
    'link', 'image', 'code-block'
  ], []);

  const quillElement = useMemo(() => (
    <ReactQuill 
      key={quillKey}
      theme="snow"
      defaultValue={content}
      onChange={setContent}
      modules={modules}
      formats={formats}
      className="h-96 mb-12"
    />
  ), [quillKey, modules, formats]);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mt-6">
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">报告标题</label>
        <input
          type="text"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="输入报告标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      <div className="mb-2">
        <label className="block text-sm font-medium text-gray-700 mb-1">报告内容 (WYSIWYG)</label>
        <div className="prose-editor">
           {quillElement}
        </div>
      </div>

      <div className="flex items-center justify-between mt-8 pt-4 border-t border-gray-100">
        <div className="text-sm text-gray-500">
          {isSaving ? '正在保存...' : lastSaved ? `上次保存: ${lastSaved.toLocaleTimeString()}` : '尚未保存'}
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => saveReport('draft')}
            disabled={isSaving}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            保存草稿
          </button>
          <button
            onClick={() => saveReport('published')}
            disabled={isSaving}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            保存并发布
          </button>
        </div>
      </div>
    </div>
  );
}
