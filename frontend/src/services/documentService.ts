import { api } from "./api";

export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  sha256_checksum: string;
  page_count: number;
  document_type: "FORMATO_UNICO" | "ATS" | "UNKNOWN" | null;
  status: "UPLOADED" | "PROCESSING" | "REVIEW_REQUIRED" | "COMPLETED" | "FAILED" | string;
  person_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentItem;
  job: {
    id: string;
    status: string;
    progress_pct: number;
    current_step: string;
  };
}

export interface CanonicalResumeData {
  document_id: string;
  person_id?: string | null;
  person: {
    first_surname: string;
    second_surname?: string | null;
    first_name: string;
    middle_name?: string | null;
    identification_type?: string | null;
    identification_number?: string | null;
    sex?: string | null;
    nationality?: string | null;
    birth_date?: string | null;
    birth_place?: string | null;
    birth_municipality?: string | null;
    birth_department?: string | null;
    birth_country?: string | null;
    military_card_number?: string | null;
    professional_card_number?: string | null;
    headline?: string | null;
    profession?: string | null;
    category?: string | null;
    full_name?: string | null;
  };
  contact: {
    address?: string | null;
    country?: string | null;
    department?: string | null;
    municipality?: string | null;
    telephone?: string | null;
    mobile_phone?: string | null;
    email?: string | null;
  };
  educations: Array<{
    id?: string;
    academic_level?: string;
    institution?: string;
    degree_title?: string;
    graduation_date?: string | null;
    is_graduated?: boolean;
    professional_card_number?: string | null;
  }>;
  work_experiences: Array<{
    id?: string;
    company_name: string;
    position: string;
    start_date?: string | null;
    end_date?: string | null;
    is_current?: boolean;
    is_public_sector?: boolean;
    total_months?: number;
    responsibilities?: string;
  }>;
  experience_summary?: {
    public_experience_months?: number;
    private_experience_months?: number;
    total_experience_months?: number;
    public_experience_display?: string;
    total_experience_display?: string;
  } | null;
  languages: Array<{
    id?: string;
    language: string;
    listening_level?: string;
    reading_level?: string;
    writing_level?: string;
  }>;
  extracted_fields_count: number;
}

export const documentService = {
  async upload(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return await api.post<DocumentUploadResponse>("/documents", formData);
  },

  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    document_type?: string;
    search?: string;
  }): Promise<DocumentListResponse> {
    return await api.get<DocumentListResponse>("/documents", { params });
  },

  async getById(id: string): Promise<any> {
    return await api.get(`/documents/${id}`);
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  },

  async classify(id: string): Promise<any> {
    return await api.post(`/documents/${id}/classify`);
  },

  async processText(id: string): Promise<any> {
    return await api.post(`/documents/${id}/process-text`);
  },

  async extractFormatoUnico(id: string): Promise<CanonicalResumeData> {
    return await api.post<CanonicalResumeData>(`/documents/${id}/extract-formato-unico`);
  },

  async extractAts(id: string): Promise<CanonicalResumeData> {
    return await api.post<CanonicalResumeData>(`/documents/${id}/extract-ats`);
  },

  async getCanonicalResume(id: string): Promise<CanonicalResumeData> {
    return await api.get<CanonicalResumeData>(`/documents/${id}/canonical-resume`);
  },

  async downloadBlob(id: string): Promise<Blob> {
    return await api.get<Blob>(`/documents/${id}/download`);
  },
};
