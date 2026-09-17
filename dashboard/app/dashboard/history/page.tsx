import { redirect } from "next/navigation";

export default function HistoryPage() {
  redirect("/dashboard/sync-history");
}
