-- turnos-saas: schema inicial
-- Ejecutar en el SQL Editor de Supabase o con `supabase db push`.

create extension if not exists btree_gist;

-- ── Tipos ────────────────────────────────────────────────────────────────────

create type plan_tier as enum ('basico', 'pro', 'premium');
create type appointment_status as enum ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED');
create type notification_type as enum ('booking_confirmation', 'reminder_24h', 'reminder_1h', 'cancellation');
create type notification_status as enum ('pending', 'sent', 'failed', 'cancelled');

-- ── Tablas ───────────────────────────────────────────────────────────────────

create table businesses (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null unique references auth.users (id) on delete cascade,
  slug text not null unique check (slug ~ '^[a-z0-9-]{3,40}$'),
  name text not null check (length(name) between 1 and 80),
  description text,
  phone text,
  address text,
  logo_url text,
  brand_primary text not null default '#7c5cff' check (brand_primary ~ '^#[0-9a-fA-F]{6}$'),
  brand_accent text not null default '#22d3ee' check (brand_accent ~ '^#[0-9a-fA-F]{6}$'),
  plan plan_tier not null default 'basico',
  timezone text not null default 'America/Argentina/Buenos_Aires',
  created_at timestamptz not null default now()
);

create table services (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  name text not null check (length(name) between 1 and 80),
  duration_minutes int not null default 60 check (duration_minutes between 15 and 240),
  price_cents int not null default 0 check (price_cents >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table working_hours (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  day_of_week smallint not null check (day_of_week between 0 and 6), -- 0 = domingo
  open_time time not null,
  close_time time not null check (close_time > open_time),
  unique (business_id, day_of_week)
);

create table appointments (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  service_id uuid not null references services (id) on delete restrict,
  customer_name text not null check (length(customer_name) between 1 and 80),
  customer_dni text not null check (length(customer_dni) between 6 and 12),
  customer_email text not null,
  customer_phone text not null,
  starts_at timestamptz not null,
  ends_at timestamptz not null check (ends_at > starts_at),
  status appointment_status not null default 'PENDING',
  price_cents int not null default 0, -- precio al momento de reservar (para ingresos)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Anti doble-reserva: dos turnos activos del mismo negocio no pueden solaparse.
  constraint no_overlap exclude using gist (
    business_id with =,
    tstzrange(starts_at, ends_at) with &&
  ) where (status in ('PENDING', 'CONFIRMED'))
);

create index idx_appt_business_start on appointments (business_id, starts_at);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  appointment_id uuid not null references appointments (id) on delete cascade,
  type notification_type not null,
  channel text not null default 'whatsapp',
  recipient_phone text not null,
  message text not null,
  status notification_status not null default 'pending',
  scheduled_at timestamptz not null,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

create index idx_notif_due on notifications (status, scheduled_at) where status = 'pending';

-- ── Row Level Security ───────────────────────────────────────────────────────

alter table businesses enable row level security;
alter table services enable row level security;
alter table working_hours enable row level security;
alter table appointments enable row level security;
alter table notifications enable row level security;

create function public.is_owner(b_id uuid) returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from businesses where id = b_id and owner_id = auth.uid()) $$;

-- businesses: el dueño todo; lectura pública (la página de reservas necesita
-- nombre, branding y slug).
create policy biz_owner_all on businesses for all to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy biz_public_read on businesses for select to anon using (true);

-- services y working_hours: lectura pública, escritura solo del dueño.
create policy svc_public_read on services for select to anon, authenticated using (true);
create policy svc_owner_write on services for insert to authenticated
  with check (is_owner(business_id));
create policy svc_owner_update on services for update to authenticated
  using (is_owner(business_id)) with check (is_owner(business_id));
create policy svc_owner_delete on services for delete to authenticated
  using (is_owner(business_id));

create policy wh_public_read on working_hours for select to anon, authenticated using (true);
create policy wh_owner_write on working_hours for insert to authenticated
  with check (is_owner(business_id));
create policy wh_owner_update on working_hours for update to authenticated
  using (is_owner(business_id)) with check (is_owner(business_id));
create policy wh_owner_delete on working_hours for delete to authenticated
  using (is_owner(business_id));

-- appointments: SIN políticas anon (los datos de clientes nunca son públicos).
-- Las reservas públicas entran por la API con service role.
create policy appt_owner_select on appointments for select to authenticated
  using (is_owner(business_id));
create policy appt_owner_update on appointments for update to authenticated
  using (is_owner(business_id)) with check (is_owner(business_id));

-- notifications: el dueño solo lee; las escribe el servidor (service role).
create policy notif_owner_read on notifications for select to authenticated
  using (is_owner(business_id));

-- ── updated_at automático ────────────────────────────────────────────────────

create function public.set_updated_at() returns trigger
language plpgsql as
$$ begin new.updated_at = now(); return new; end $$;

create trigger trg_appointments_updated_at
  before update on appointments
  for each row execute function public.set_updated_at();
