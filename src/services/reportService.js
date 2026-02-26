import { backendClient } from './backend';

export const reportService = {
  createReport: (data) => backendClient.request('POST', '/api/reports', data),
  getReports: (params) => {
    const queryString = new URLSearchParams(params).toString();
    return backendClient.request('GET', `/api/reports?${queryString}`);
  },
  getReport: (id) => backendClient.request('GET', `/api/reports/${id}`),
  updateReport: (id, data) => backendClient.request('PUT', `/api/reports/${id}`, data),
  deleteReport: (id) => backendClient.request('DELETE', `/api/reports/${id}`),
};
