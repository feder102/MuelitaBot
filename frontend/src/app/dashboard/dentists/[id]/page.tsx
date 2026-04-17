'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { dentists, ApiError } from '@/lib/api';

export default function DentistEditPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({ name: '', calendar_id: '', active_status: true });

  useEffect(() => {
    const load = async () => {
      try {
        const result = await dentists.list();
        const dentist = result.items.find((d: any) => d.id === id);
        if (dentist) {
          setData(dentist);
          setFormData({
            name: dentist.name,
            calendar_id: dentist.calendar_id,
            active_status: dentist.active_status,
          });
        }
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await dentists.update(id, formData);
      router.push('/dashboard/dentists');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div>Cargando...</div>;
  if (!data) return <div>No encontrado</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Editar Odontólogo</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 max-w-2xl">
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-bold mb-2">Nombre</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
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
              disabled={submitting}
            />
          </div>
          <div className="mb-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.active_status}
                onChange={(e) => setFormData({ ...formData, active_status: e.target.checked })}
                className="mr-2"
                disabled={submitting}
              />
              <span className="text-sm font-medium">Activo</span>
            </label>
          </div>
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md disabled:opacity-50"
            >
              {submitting ? 'Guardando...' : 'Guardar'}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md"
            >
              Volver
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
