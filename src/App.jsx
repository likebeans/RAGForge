import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import KnowledgeOverview from './pages/KnowledgeOverview'
import KnowledgeDocs from './pages/KnowledgeDocs'
import KnowledgeUpload from './pages/KnowledgeUpload'
import Settings from './pages/Settings'
import ApiKeyManagement from './pages/ApiKeyManagement'
import UserRoleManagement from './pages/UserRoleManagement'
import DataManagement from './pages/DataManagement'
import MasterDataManagement from './pages/MasterDataManagement'
import ReportsList from './pages/ReportsList'
import ReportEditor from './pages/ReportEditor'
import ReportDetail from './pages/ReportDetail'
import ReportAssistant from './pages/ReportAssistant'
import MainLayout from './layouts/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="reports" element={<ReportsList />} />
          <Route path="reports/new" element={<ReportEditor />} />
          <Route path="reports/assistant" element={<ReportAssistant />} />
          <Route path="reports/:reportId" element={<ReportDetail />} />
          <Route path="reports/:reportId/edit" element={<ReportEditor />} />
          <Route path="knowledge" element={<KnowledgeOverview />} />
          <Route path="knowledge/docs" element={<KnowledgeDocs />} />
          <Route path="knowledge/upload" element={<KnowledgeUpload />} />
          <Route path="projects" element={<DataManagement />} />
          <Route path="master-data" element={<MasterDataManagement />} />
          <Route path="data" element={<DataManagement />} />
          <Route path="admin/api-keys" element={<ApiKeyManagement />} />
          <Route path="admin/users" element={<UserRoleManagement />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
