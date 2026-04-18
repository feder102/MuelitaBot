'use client';

import { useEffect, useState } from 'react';
import {
  appointments,
  dentists,
  type AppointmentListItem,
  type AppointmentListResponse,
  type DentistListResponse,
  ApiError,
} from '@/lib/api';

export default function DashboardPage() {
  const [appointmentData, setAppointmentData] = useState<AppointmentListResponse | null>(null);
  const [dentistData, setDentistData] = useState<DentistListResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [appts, docs] = await Promise.all([
          appointments.list(),
          dentists.list(),
        ]);
        setAppointmentData(appts);
        setDentistData(docs);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div>Cargando...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Turnos Próximos</h2>
          <p className="text-4xl font-bold text-blue-600">
            {appointmentData?.items?.filter((a: AppointmentListItem) => a.status === 'CONFIRMED').length || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Odontólogos</h2>
          <p className="text-4xl font-bold text-green-600">
            {dentistData?.items?.length || 0}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Próximos Turnos</h2>
        {appointmentData?.items && appointmentData.items.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Paciente</th>
                <th className="text-left py-2">Odontólogo</th>
                <th className="text-left py-2">Fecha</th>
                <th className="text-left py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {appointmentData.items.slice(0, 5).map((a: AppointmentListItem) => (
                <tr key={a.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{a.patient?.first_name} {a.patient?.last_name}</td>
                  <td className="py-2">{a.dentist?.name}</td>
                  <td className="py-2">{a.slot_date} {a.start_time}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-sm font-semibold ${
                      a.status === 'CONFIRMED'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">No hay turnos próximos</p>
        )}
      </div>
    </div>
  );
}
