import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  },
);

export const dataApi = {
  getStats: () => api.get("/data/stats"),
  generateData: (count: number) =>
    api.post("/data/generate", { employee_count: count }),
  getDepartments: () => api.get("/data/departments"),
};

export const analysisApi = {
  recruitment: (params = {}) => api.post("/analysis/recruitment", params),
  performance: (params = {}) => api.post("/analysis/performance", params),
  talentRisk: (params = {}) => api.post("/analysis/talent-risk", params),
  orgHealth: (params = {}) => api.post("/analysis/org-health", params),
};

export const reportsApi = {
  generate: (params = {}) => api.post("/reports/generate", params),
  getActionList: (id: string) => api.get(`/reports/action-list/${id}`),
};

export default api;
