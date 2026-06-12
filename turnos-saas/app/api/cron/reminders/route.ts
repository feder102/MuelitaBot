import { NextResponse } from "next/server";
import { sendDueNotifications } from "@/lib/notifications/dispatch";
import { createAdminClient } from "@/lib/supabase/admin";

export async function GET(request: Request) {
  const secret = process.env.CRON_SECRET;
  const auth = request.headers.get("authorization");
  if (!secret || auth !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "No autorizado" }, { status: 401 });
  }

  try {
    const stats = await sendDueNotifications(createAdminClient());
    return NextResponse.json({ ok: true, ...stats });
  } catch (err) {
    console.error("Error despachando recordatorios:", err);
    return NextResponse.json(
      { error: "Error despachando recordatorios" },
      { status: 500 },
    );
  }
}
