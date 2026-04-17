'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { appointments, ApiError } from '@/lib/api';

export default function AppointmentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState<'cancel' | 'delete' | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await appointments.get(id);
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

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await appointments.cancel(id);
      router.push('/dashboard/appointments');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setActionLoading(false);
      setShowConfirm(null);
    }
  };

  const handleDelete = async () => {
    setActionLoading(true);
    try {
      await appointments.delete(id);
      router.push('/dashboard/appointments');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setActionLoading(false);
      setShowConfirm(null);
    }
  };

  if (loading) return <div>Cargando...</div>;
  if (!data) return <div>No encontrado</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Turno</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          Error: {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600">Paciente</p>
            <p className="text-lg font-semibold">{data.patient?.first_name} {data.patient?.last_name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Odontólogo</p>
            <p className="text-lg font-semibold">{data.dentist?.name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Fecha</p>
            <p className="text-lg font-semibold">{data.slot_date}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Hora</p>
            <p className="text-lg font-semibold">{data.start_time} - {data.end_time}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Motivo</p>
            <p className="text-lg font-semibold">{data.reason}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Estado</p>
            <p className={`text-lg font-semibold ${
              data.status === 'confirmed' ? 'text-green-600' : 'text-gray-600'
            }`}>
              {data.status}
            </p>
          </div>
        </div>

        <div className="flex gap-4">
          {data.status === 'confirmed' && (
            <button
              onClick={() => setShowConfirm('cancel')}
              disabled={actionLoading}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md disabled:opacity-50"
            >
              {actionLoading ? 'Procesando...' : 'Cancelar Turno'}
            </button>
          )}

          <button
            onClick={() => setShowConfirm('delete')}
            disabled={actionLoading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md disabled:opacity-50"
          >
            {actionLoading ? 'Procesando...' : 'Eliminar'}
          </button>

          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md"
          >
            Volver
          </button>
        </div>
      </div>

      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-sm">
            <p className="mb-6">
              {showConfirm === 'cancel'
                ? '¿Estás seguro que deseas cancelar este turno?'
                : '¿Estás seguro que deseas eliminar este turno?'}
            </p>
            <div className="flex gap-4">
              <button
                onClick={showConfirm === 'cancel' ? handleCancel : handleDelete}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md disabled:opacity-50"
              >
                {actionLoading ? 'Procesando...' : 'Confirmar'}
              </button>
              <button
                onClick={() => setShowConfirm(null)}
                disabled={actionLoading}
                className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md disabled:opacity-50"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
