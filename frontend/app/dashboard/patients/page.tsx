'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { patients, type PatientListResponse, type PatientSummary, ApiError } from '@/lib/api';

export default function PatientsPage() {
  const [data, setData] = useState<PatientListResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await patients.list();
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
  }, []);

  if (loading) return <div>Cargando...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Pacientes</h1>

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
                <th className="text-left px-6 py-3">Nombre</th>
                <th className="text-left px-6 py-3">Usuario Telegram</th>
                <th className="text-left px-6 py-3">Username</th>
                <th className="text-left px-6 py-3">Última Interacción</th>
                <th className="text-left px-6 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p: PatientSummary) => (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-3">{p.first_name} {p.last_name}</td>
                  <td className="px-6 py-3 font-mono text-sm">{p.telegram_user_id}</td>
                  <td className="px-6 py-3">{p.username || '-'}</td>
                  <td className="px-6 py-3 text-sm">{p.last_interaction || '-'}</td>
                  <td className="px-6 py-3">
                    <Link
                      href={`/dashboard/patients/${p.id}`}
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
        <p className="text-gray-500">No hay pacientes</p>
      )}
    </div>
  );
}
