import { api } from "./api";

export interface ReviewField {
  id: string;
  extraction_id: string;
  field_name: string;
  raw_value: string | null;
  normalized_value: string | null;
  page_number: number;
  bounding_box: Record<string, any> | null;
  confidence: number;
  review_status: "PENDING" | "ACCEPTED" | "CORRECTED" | "REJECTED";
  corrected_value?: string | null;
  corrected_by?: string | null;
  corrected_at?: string | null;
  correction_note?: string | null;
  created_at: string;
}

export interface ReviewSummary {
  document_id: string;
  total_fields: number;
  pending_count: number;
  accepted_count: number;
  corrected_count: number;
  rejected_count: number;
  completion_pct: number;
  is_complete: boolean;
}

export const reviewService = {
  async getFieldsForDocument(
    documentId: string,
    params?: { status?: string; page_number?: number }
  ): Promise<ReviewField[]> {
    return await api.get<ReviewField[]>(`/documents/${documentId}/review-fields`, { params });
  },

  async acceptField(documentId: string, fieldId: string, notes?: string): Promise<ReviewField> {
    return await api.post<ReviewField>(
      `/documents/${documentId}/review-fields/${fieldId}/accept`,
      { notes }
    );
  },

  async correctField(
    documentId: string,
    fieldId: string,
    correctedValue: string,
    note?: string
  ): Promise<ReviewField> {
    return await api.post<ReviewField>(
      `/documents/${documentId}/review-fields/${fieldId}/correct`,
      { corrected_value: correctedValue, note }
    );
  },

  async rejectField(documentId: string, fieldId: string, reason?: string): Promise<ReviewField> {
    return await api.post<ReviewField>(
      `/documents/${documentId}/review-fields/${fieldId}/reject`,
      { reason }
    );
  },

  async batchReview(
    documentId: string,
    fieldIds: string[],
    action: "ACCEPT" | "REJECT"
  ): Promise<any> {
    return await api.post(`/documents/${documentId}/review-fields/batch`, {
      field_ids: fieldIds,
      action,
    });
  },

  async getSummary(documentId: string): Promise<ReviewSummary> {
    return await api.get<ReviewSummary>(`/documents/${documentId}/review-summary`);
  },

  async finalizeReview(documentId: string, notes?: string): Promise<any> {
    return await api.post(`/documents/${documentId}/finalize-review`, { notes });
  },
};
