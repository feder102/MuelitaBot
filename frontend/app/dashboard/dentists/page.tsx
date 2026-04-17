'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { dentists, ApiError } from '@/lib/api';

export default function DentistsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', calendar_id: '' });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await dentists.list();
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await dentists.create(formData);
      setFormData({ name: '', calendar_id: '' });
      setShowForm(false);
      const result = await dentists.list();
      setData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Odontólogos</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
        >
          {showForm ? 'Cancelar' : 'Agregar Odontólogo'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-sm font-bold mb-2">Nombre</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
                disabled={submitting}
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-bold mb-2">ID Calendario Google</label>
              <input
                type="text"
                value={formData.calendar_id}
                onChange={(e) => setFormData({ ...formData, calendar_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                required
                disabled={submitting}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md disabled:opacity-50"
            >
              {submitting ? 'Guardando...' : 'Guardar'}
            </button>
          </form>
        </div>
      )}

      {data?.items && data.items.length > 0 ? (
        <div className="bg-white rounded-lg shadow">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-6 py-3">Nombre</th>
                <th className="text-left px-6 py-3">Calendario Google</th>
                <th className="text-left px-6 py-3">Estado</th>
                <th className="text-left px-6 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((d: any) => (
                <tr key={d.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-3">{d.name}</td>
                  <td className="px-6 py-3 text-sm">{d.calendar_id}</td>
                  <td className="px-6 py-3">
                    <span className={`px-2 py-1 rounded text-sm font-semibold ${
                      d.active_status
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {d.active_status ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <Link
                      href={`/dashboard/dentists/${d.id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      Editar
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No hay odontólogos</p>
      )}
    </div>
  );
}
