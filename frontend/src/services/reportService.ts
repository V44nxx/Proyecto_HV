import { api } from "./api";

export interface ReportCatalogItem {
  report_type: string;
  title: string;
  description: string;
  supported_formats: string[];
  filter_fields: string[];
}

export interface ReportColumn {
  key: string;
  label: string;
  align: string;
}

export interface ReportPreviewResponse {
  report_type: string;
  title: string;
  description: string;
  generated_at: string;
  columns: ReportColumn[];
  rows: Array<Record<string, any>>;
  total_records: number;
}

export const reportService = {
  async getAvailableReports(): Promise<ReportCatalogItem[]> {
    return await api.get<ReportCatalogItem[]>("/reports/available");
  },

  async getPreview(reportType: string, filters: Record<string, any> = {}): Promise<ReportPreviewResponse> {
    return await api.post<ReportPreviewResponse>("/reports/preview", {
      report_type: reportType,
      filters,
    });
  },

  async exportReport(
    reportType: string,
    format: "EXCEL" | "PDF",
    filters: Record<string, any> = {}
  ): Promise<Blob> {
    return await api.post<Blob>("/reports/export", {
      report_type: reportType,
      report_format: format,
      filters,
    });
  },
};
