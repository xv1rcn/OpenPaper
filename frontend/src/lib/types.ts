export interface Paper {
  speedread_status?: string;
  file_key: string;
  title: string;
  authors: string;
  year: string;
  venue: string;
  tags: string[];
  pdf: string;
  read: boolean;
  notes: string;
  bib: string;
  added_at: string;
}
export interface RecycleItem {
  id: string;
  title: string;
  deleted_at: string;
  item_type: "paper" | "tag" | "speedread";
  tag?: string;
  affected_count?: number;
}
export type Collection =
  "all" | "unread" | "read" | "recycle" | "stats" | "tools";
export type Sort =
  | "recent"
  | "oldest"
  | "title"
  | "title-desc"
  | "year"
  | "year-asc"
  | "venue"
  | "venue-desc";
