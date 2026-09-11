import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from './api.config';

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
  constructor(private http: HttpClient) {}

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

  obtenerCitaPorId(id: number, token: string): Observable<any> {
    // El backend ahora exige el token del paciente y verifica que la cita
    // le pertenezca (ver Depends(verificar_paciente) en main.py).
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });
    return this.http.get(`${API_URL}/citas/${id}`, { headers });
  }

  citasDePaciente(pacienteId: number): Observable<any[]> {
    return this.http.get<any[]>(`${API_URL}/citas/paciente/${pacienteId}`);
  }

  facturasDePaciente(pacienteId: number): Observable<any[]> {
    return this.http.get<any[]>(`${API_URL}/facturas/paciente/${pacienteId}`);
  }

  listarTodosLosPacientesAdmin(token: string): Observable<any[]> {
    // El backend ahora exige un token de admin en el encabezado
    // Authorization (ver Depends(verificar_admin) en main.py).
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });
    return this.http.get<any[]>(`${API_URL}/admin/pacientes`, { headers });
  }
}
