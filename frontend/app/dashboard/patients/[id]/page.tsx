'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { patients, type PatientAppointment, type PatientDetail, ApiError } from '@/lib/api';

export default function PatientDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  const [data, setData] = useState<PatientDetail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await patients.get(id);
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
  }, [id]);

  if (loading) return <div>Cargando...</div>;
  if (!data) return <div>No encontrado</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Paciente</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Nombre</p>
            <p className="text-lg font-semibold">{data.first_name} {data.last_name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Usuario Telegram</p>
            <p className="text-lg font-semibold font-mono">{data.telegram_user_id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Username</p>
            <p className="text-lg font-semibold">{data.username || '-'}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Turnos</h2>
        {data.appointments && data.appointments.length > 0 ? (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-6 py-3">Odontólogo</th>
                <th className="text-left px-6 py-3">Fecha</th>
                <th className="text-left px-6 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {data.appointments.map((a: PatientAppointment) => (
                <tr key={a.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-3">{a.dentist?.name || '-'}</td>
                  <td className="px-6 py-3">{a.slot_date}</td>
                  <td className="px-6 py-3">
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
          <p className="text-gray-500">Sin turnos</p>
        )}
      </div>

      <button
        onClick={() => router.back()}
        className="mt-6 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md"
      >
        Volver
      </button>
    </div>
  );
}
