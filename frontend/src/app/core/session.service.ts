import { Injectable } from '@angular/core';

/**
 * Manejo de "sesión" en el cliente.
 *
 * SOLUCIÓN DE REFERENCIA: además de guardar los datos del paciente/
 * administrador para la interfaz (mostrar u ocultar botones), ahora se
 * guarda el JWT (`token`) emitido por el backend en el login. Ese token es
 * el que realmente autentica cada solicitud (ver auth.interceptor.ts): el
 * backend ahora SÍ verifica la sesión en cada endpoint sensible, en lugar
 * de confiar únicamente en lo que el cliente afirma tener guardado.
 */

export interface PacienteSesion {
  tipo: 'paciente';
  id: number;
  nombre: string;
  cedula: string;
  token: string;
}

export interface AdminSesion {
  tipo: 'admin';
  id: number;
  usuario: string;
  rol: string;
  token: string;
}

export type Sesion = PacienteSesion | AdminSesion;

const CLAVE_STORAGE = 'vidaplena_sesion';

@Injectable({ providedIn: 'root' })
export class SessionService {
  guardarSesion(sesion: Sesion): void {
    localStorage.setItem(CLAVE_STORAGE, JSON.stringify(sesion));
  }

  obtenerSesion(): Sesion | null {
    const crudo = localStorage.getItem(CLAVE_STORAGE);
    return crudo ? (JSON.parse(crudo) as Sesion) : null;
  }

  obtenerToken(): string | null {
    return this.obtenerSesion()?.token ?? null;
  }

  esAdmin(): boolean {
    return this.obtenerSesion()?.tipo === 'admin';
  }

  cerrarSesion(): void {
    localStorage.removeItem(CLAVE_STORAGE);
  }
}
