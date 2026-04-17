'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { appointments, ApiError } from '@/lib/api';

export default function AppointmentsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const result = await appointments.list(status ? { status } : undefined);
        setData(result);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [status]);

  if (loading) return <div>Cargando...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Turnos</h1>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="px-4 py-2 border rounded-md"
        >
          <option value="">Todos</option>
          <option value="confirmed">Confirmados</option>
          <option value="cancelled">Cancelados</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      {data?.items && data.items.length > 0 ? (
        <div className="bg-white rounded-lg shadow">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-6 py-3">Paciente</th>
                <th className="text-left px-6 py-3">Odontólogo</th>
                <th className="text-left px-6 py-3">Fecha</th>
                <th className="text-left px-6 py-3">Motivo</th>
                <th className="text-left px-6 py-3">Estado</th>
                <th className="text-left px-6 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((a: any) => (
                <tr key={a.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-3">{a.patient?.first_name} {a.patient?.last_name}</td>
                  <td className="px-6 py-3">{a.dentist?.name}</td>
                  <td className="px-6 py-3">{a.slot_date} {a.start_time}</td>
                  <td className="px-6 py-3 text-sm">{a.reason}</td>
                  <td className="px-6 py-3">
                    <span className={`px-2 py-1 rounded text-sm font-semibold ${
                      a.status === 'confirmed'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <Link
                      href={`/dashboard/appointments/${a.id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No hay turnos</p>
      )}
    </div>
  );
}
