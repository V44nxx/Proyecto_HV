import { api } from "./api";

export interface CandidateItem {
  id: string;
  first_name?: string | null;
  middle_name?: string | null;
  first_surname?: string | null;
  second_surname?: string | null;
  full_name: string;
  identification_type?: string | null;
  identification_number?: string | null;
  profession_name?: string | null;
  primary_profession?: string | null;
  category_name?: string | null;
  primary_category?: string | null;
  department?: string | null;
  municipality?: string | null;
  highest_academic_level?: string | null;
  top_education?: string | null;
  total_experience_years?: number | null;
  document_count: number;
  documents_count?: number;
}

export interface CandidateSearchResponse {
  items: CandidateItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FacetCount {
  id?: string;
  label: string;
  count: number;
}

export interface SearchFacetsResponse {
  categories: FacetCount[];
  professions: FacetCount[];
  academic_levels: FacetCount[];
  departments: FacetCount[];
}

export interface FilterOptionsResponse {
  categories: Array<{ id: string; name: string; code?: string; professions?: Array<{ id: string; name: string; category_id?: string }> }>;
  professions: Array<{ id: string; name: string; category_id?: string }>;
  academic_levels: string[];
  departments: string[];
}

export interface CandidateFullDetail {
  id: string;
  first_name: string;
  middle_name?: string | null;
  first_surname: string;
  second_surname?: string | null;
  full_name: string;
  identification_type?: string | null;
  identification_number?: string | null;
  sex?: string | null;
  nationality?: string | null;
  birth_date?: string | null;
  profession_name?: string | null;
  category_name?: string | null;
  contact?: {
    address?: string | null;
    department?: string | null;
    municipality?: string | null;
    telephone?: string | null;
    mobile_phone?: string | null;
    email?: string | null;
  } | null;
  educations: Array<{
    academic_level?: string;
    institution?: string;
    degree_title?: string;
    graduation_date?: string | null;
    is_graduated?: boolean;
    professional_card_number?: string | null;
  }>;
  work_experiences: Array<{
    company_name: string;
    position: string;
    start_date?: string | null;
    end_date?: string | null;
    is_current?: boolean;
    is_public_sector?: boolean;
    total_months?: number;
    responsibilities?: string;
  }>;
  languages: Array<{
    language: string;
    listening_level?: string;
    reading_level?: string;
    writing_level?: string;
  }>;
  skills: string[];
  executive_summary?: string | null;
  documents: Array<{
    id: string;
    filename: string;
    document_type?: string;
    created_at: string;
  }>;
}

export const searchService = {
  async searchCandidates(params?: {
    q?: string;
    profession_id?: string;
    category_id?: string;
    academic_level?: string;
    department?: string;
    municipality?: string;
    min_experience_years?: number;
    max_experience_years?: number;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: "asc" | "desc";
  }): Promise<CandidateSearchResponse> {
    return await api.get<CandidateSearchResponse>("/search/candidates", { params });
  },

  async getCandidateDetail(personId: string): Promise<CandidateFullDetail> {
    return await api.get<CandidateFullDetail>(`/search/candidates/${personId}`);
  },

  async getFacets(q?: string): Promise<SearchFacetsResponse> {
    return await api.get<SearchFacetsResponse>("/search/facets", { params: { q } });
  },

  async getFilterOptions(): Promise<FilterOptionsResponse> {
    return await api.get<FilterOptionsResponse>("/search/filter-options");
  },
};
