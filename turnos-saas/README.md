# TurnosYa — SaaS multi-tenant de reserva de turnos

Sistema de reserva de turnos online construido con **Next.js (App Router) + Supabase**, con estilo dark premium y UI en español.

## Funcionalidades

- **Multi-tenant**: cada negocio se registra, tiene su página pública (`/{slug}`) y gestiona su propia agenda. Aislamiento por Row Level Security.
- **Página pública de reservas**: los clientes (sin login) eligen servicio, día y horario, y confirman con nombre, DNI, email y teléfono.
- **Dashboard del profesional**: turnos del día, agenda semanal, ingresos del mes, confirmación/cancelación de turnos.
- **Configuración**: servicios (duración y precio), horarios de atención, perfil, logo y colores de marca.
- **Notificaciones por WhatsApp** (capa abstracta, proveedor simulado): confirmación al reservar, recordatorio 24 h antes y 1 h antes.
- **Planes Básico / Pro / Premium** con límites y features diferenciados (sin pasarela de pago en esta versión).

## Setup

### 1. Crear el proyecto de Supabase

1. Creá un proyecto en [supabase.com](https://supabase.com).
2. Abrí el **SQL Editor** y ejecutá el contenido de [`supabase/migrations/0001_init.sql`](supabase/migrations/0001_init.sql). (Alternativa con CLI: `supabase link --project-ref <ref> && supabase db push`.)
3. En **Authentication → Providers**, verificá que el proveedor **Email** esté habilitado. No hace falta desactivar la confirmación de email: el registro usa `auth.admin.createUser` con `email_confirm: true`.

### 2. Variables de entorno

```bash
cp .env.example .env.local
```

Completá con los valores de **Project Settings → API** de tu proyecto:

| Variable | Descripción |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave pública (anon) |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service role — **solo servidor** |
| `CRON_SECRET` | Secreto aleatorio para la ruta del cron |
| `NOTIFICATION_PROVIDER` | `console` (simulado) |

### 3. Correr en desarrollo

```bash
npm install
npm run dev
```

Abrí [http://localhost:3000](http://localhost:3000), registrá un negocio y empezá a recibir reservas en `/{tu-slug}`.

## Recordatorios (cron)

Los recordatorios quedan agendados en la tabla `notifications` y los despacha `GET /api/cron/reminders`:

- **En Vercel**: `vercel.json` ya define el cron cada 10 minutos. Configurá `CRON_SECRET` en las variables de entorno del proyecto (Vercel lo envía automáticamente como `Authorization: Bearer`).
- **En local** (o para probar):

  ```bash
  curl -H "Authorization: Bearer $CRON_SECRET" http://localhost:3000/api/cron/reminders
  ```

- **Alternativa sin Vercel** (pg_cron + pg_net en Supabase):

  ```sql
  select cron.schedule(
    'recordatorios-turnos',
    '*/10 * * * *',
    $$ select net.http_post(
         url := 'https://tu-app.com/api/cron/reminders',
         headers := '{"Authorization": "Bearer TU_CRON_SECRET"}'::jsonb
       ) $$
  );
  ```

## Notificaciones WhatsApp

El envío está detrás de la interfaz `NotificationProvider` (`lib/notifications/types.ts`). El proveedor por defecto (`console`) simula el envío logueando el mensaje. Para integrar Twilio o la Cloud API de Meta:

1. Implementá la interfaz en `lib/notifications/<proveedor>-provider.ts`.
2. Registralo en la factory `getNotificationProvider()` (`lib/notifications/dispatch.ts`).
3. Seteá `NOTIFICATION_PROVIDER=<proveedor>`.

## Decisiones de diseño

- **Reservas públicas vía API con service role**: la tabla `appointments` no tiene políticas para `anon` (los datos de clientes nunca son legibles públicamente). `POST /api/bookings` valida horario, disponibilidad y límite de plan en el servidor antes de insertar.
- **Anti doble-reserva**: una *exclusion constraint* de PostgreSQL (`tstzrange && tstzrange` por negocio) garantiza a nivel de base que dos turnos activos no se solapen, incluso ante requests simultáneas (la segunda recibe 409).
- **Zona horaria**: Argentina no tiene horario de verano, por lo que se usa el offset fijo `-03:00` (`lib/dates.ts`) sin librerías de timezone. Si el país volviera a tener DST, habría que migrar a una librería con base de datos de zonas.
- **Planes en código**: los límites viven en `lib/plans.ts` (única fuente para la página de precios y los puntos de enforcement); el plan de cada negocio se guarda en `businesses.plan`.

## Stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · Supabase (Auth + Postgres + RLS) · zod
