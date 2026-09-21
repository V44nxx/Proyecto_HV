import { api } from "./api";

export interface DashboardKpis {
  total_documents: number;
  total_persons: number;
  total_professionals: number;
  processed_documents: number;
  documents_requiring_review: number;
  extraction_success_rate: number;
}

export interface DistributionItem {
  label: string;
  count: number;
  percentage: number;
}

export interface DashboardDistributions {
  by_format: DistributionItem[];
  by_category: DistributionItem[];
  top_professions: DistributionItem[];
  by_academic_level: DistributionItem[];
  by_experience: Record<string, number>;
  by_geography: DistributionItem[];
}

export interface PendingReviewItem {
  document_id: string;
  filename: string;
  document_type?: string | null;
  uploaded_at: string;
  pending_fields_count: number;
  lowest_confidence: number;
}

export interface RecentActivityItem {
  document_id: string;
  filename: string;
  document_type?: string | null;
  candidate_name?: string | null;
  status: string;
  progress_pct: number;
  updated_at: string;
}

export interface DashboardOverview {
  kpis: DashboardKpis;
  distributions: DashboardDistributions;
  pending_reviews: PendingReviewItem[];
  recent_activity: RecentActivityItem[];
}

export const dashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    return await api.get<DashboardOverview>("/dashboard/overview");
  },

  async getKpis(): Promise<DashboardKpis> {
    return await api.get<DashboardKpis>("/dashboard/kpis");
  },

  async getDistributions(): Promise<DashboardDistributions> {
    return await api.get<DashboardDistributions>("/dashboard/distributions");
  },

  async getPendingReviews(limit: number = 10): Promise<PendingReviewItem[]> {
    return await api.get<PendingReviewItem[]>("/dashboard/pending-reviews", { params: { limit } });
  },

  async getRecentActivity(limit: number = 10): Promise<RecentActivityItem[]> {
    return await api.get<RecentActivityItem[]>("/dashboard/recent-activity", { params: { limit } });
  },
};
