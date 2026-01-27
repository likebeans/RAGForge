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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="knowledge" element={<KnowledgeOverview />} />
          <Route path="knowledge/docs" element={<KnowledgeDocs />} />
          <Route path="knowledge/upload" element={<KnowledgeUpload />} />
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
