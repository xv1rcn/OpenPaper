export interface Paper {
  file_key: string;
  title: string;
  authors: string;
  year: string;
  venue: string;
  tags: string[];
  pdf: string;
  read: boolean;
  notes: string;
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
export type Collection = "all" | "unread" | "read" | "recycle";
export type Sort = "recent" | "title" | "year";
