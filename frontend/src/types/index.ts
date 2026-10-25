export interface SentimentScores {
  negative: number;
  neutral: number;
  positive: number;
}

export interface FeedbackSubmission {
  id: number;
  department_name: string;
  is_other: boolean;
  subject_name?: string | null;
  instructor_name?: string | null;
  rating: number;
  feedback_text: string;
  sentiment_label: 'Positive' | 'Negative' | 'Neutral';
  sentiment_detail: string;
  sentiment_confidence: number;
  sentiment_scores?: SentimentScores;
  is_mixed: boolean;
  cluster_id?: number | null;
  topic_label?: string | null;
  created_at: string;
}

export interface TopicCluster {
  cluster_id: number;
  topic_label: string;
  comment_count: number;
  sentiment_distribution: {
    positive: number;
    negative: number;
    neutral: number;
  };
  representative_comments: string[];
  supporting_comments: FeedbackSubmission[];
  top_keywords: string[];
  departments: string[];
  subjects: string[];
  instructors: string[];
}

export interface OverviewMetrics {
  total_submissions: number;
  sentiment_counts: {
    positive: number;
    negative: number;
    neutral: number;
    mixed: number;
  };
  rating_distribution: {
    [key: number]: number;
  };
  instructor_count: number;
  topic_count: number;
}

export interface DepartmentOverviewItem {
  id: number;
  name: string;
  code?: string;
  subject_count: number;
  instructor_count: number;
  feedback_count: number;
}

export interface OtherOverviewItem {
  name: string;
  description: string;
  total_submissions: number;
  positive: number;
  negative: number;
  neutral: number;
  mixed: number;
}

export interface DepartmentsOverviewResponse {
  departments: DepartmentOverviewItem[];
  other: OtherOverviewItem;
}

export interface SimpleInstructor {
  id: number;
  name: string;
}

export interface SimpleSubject {
  id: number;
  name: string;
  code?: string;
}

export interface Subject {
  id: number;
  name: string;
  code?: string;
  department_id: number;
  department_name?: string;
  is_active: boolean;
  created_at: string;
  instructors: SimpleInstructor[];
}

export interface Instructor {
  id: number;
  name: string;
  department_id?: number;
  department_name?: string;
  department?: string;
  is_active: boolean;
  created_at: string;
  subjects: SimpleSubject[];
}

export interface Department {
  id: number;
  name: string;
  code?: string;
  is_active: boolean;
  created_at: string;
  subject_count?: number;
  instructor_count?: number;
  feedback_count?: number;
}
