import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from './api.config';
import { SessionService } from './session.service';

export interface PacienteRegistro {
  nombre: string;
  cedula: string;
  telefono?: string;
  correo?: string;
  contrasena: string;
}

export interface LoginRequest {
  identificador: string;
  contrasena: string;
}

export interface CitaCreate {
  paciente_id: number;
  fecha: string; // yyyy-MM-dd
  hora: string; // HH:mm:ss
  medico: string;
  motivo_consulta?: string;
  diagnostico?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(
  private http: HttpClient,
  private session: SessionService
) {}

  registrarPaciente(datos: PacienteRegistro): Observable<any> {
    return this.http.post(`${API_URL}/pacientes/registro`, datos);
  }

  loginPaciente(datos: LoginRequest): Observable<any> {
    return this.http.post(`${API_URL}/login/paciente`, datos);
  }

  loginAdmin(datos: LoginRequest): Observable<any> {
    return this.http.post(`${API_URL}/login/admin`, datos);
  }

  buscarPacientePorCedula(cedula: string): Observable<any[]> {
    return this.http.get<any[]>(`${API_URL}/pacientes/buscar`, { params: { cedula } });
  }

  crearCita(datos: CitaCreate): Observable<any> {
    return this.http.post(`${API_URL}/citas`, datos);
  }

  obtenerCitaPorId(id: number): Observable<any> {
  const sesion = this.session.obtenerSesion();

  const token =
    sesion?.tipo === 'paciente'
      ? sesion.token
      : '';

  return this.http.get(
    `${API_URL}/citas/${id}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
}

  citasDePaciente(pacienteId: number): Observable<any[]> {
    return this.http.get<any[]>(`${API_URL}/citas/paciente/${pacienteId}`);
  }

  facturasDePaciente(pacienteId: number): Observable<any[]> {
    return this.http.get<any[]>(`${API_URL}/facturas/paciente/${pacienteId}`);
  }

  listarTodosLosPacientesAdmin(): Observable<any[]> {
  const sesion = this.session.obtenerSesion();

  const token =
    sesion?.tipo === 'admin'
      ? sesion.token
      : '';

  return this.http.get<any[]>(
    `${API_URL}/admin/pacientes`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
}
  }

